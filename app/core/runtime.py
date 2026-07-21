import logging
from collections import Counter
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.contracts.loop_contract import LoopContext, RunResult, ArtifactRef, ToolCallSummary, UsageInfo
from app.contracts.validation import validate_payload
from app.core.artifacts import ArtifactWriter
from app.core.executor import StepExecutor
from app.core.planner import SimplePlanner
from app.db.repositories import Repository
from app.domains.registry import DomainRegistry
from app.evals.runner import EvaluationRunner
from app.model_gateway import ModelGateway, complete_simple, get_model_gateway
from app.settings import get_settings
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry
from app.tools.intravision_tools import build_run_registry
from app.core.tool_loop import run_tool_loop

logger = logging.getLogger(__name__)


class AgentRuntime:
    def __init__(
        self,
        domain_registry: DomainRegistry,
        tool_registry: ToolRegistry,
        repository: Repository,
        model_gateway: ModelGateway | None = None,
    ) -> None:
        self.domain_registry = domain_registry
        self.tool_registry = tool_registry
        self.repository = repository
        self.settings = get_settings()
        self.planner = SimplePlanner()
        self.executor = StepExecutor(ToolExecutor(tool_registry, repository), model_gateway or get_model_gateway())
        self.artifacts = ArtifactWriter()
        self.evals = EvaluationRunner()

    def run_agent(
        self,
        agent_id: str,
        input_payload: dict[str, Any],
        *,
        model_override: str | None = None,
        loop_context: LoopContext | None = None,
        max_steps: int | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        agent = self.domain_registry.get_agent(agent_id)
        validate_payload(agent.input_schema, input_payload, "agent input")
        run_id = str(uuid4())
        started_at = datetime.now(UTC).isoformat()
        plan = self.planner.create_plan(agent)

        if loop_context is not None:
            logger.info(
                "Loop run started",
                extra={"loop_id": loop_context.loop_id, "iteration_index": loop_context.iteration_index, "run_id": run_id},
            )

        # When Intravision passes host tools for this run, use the dynamic LLM
        # tool-calling loop so the agent can actually perform actions (create pages,
        # tasks, ...) instead of the static reasoning-only plan.
        iv_tools = input_payload.get("_iv_tools")
        iv_run_id = input_payload.get("_iv_run_id")
        use_tool_loop = bool(iv_tools) and bool(iv_run_id) and bool(self.settings.intravision_base_url)

        # Pre-insert the agent_run row so tool_calls FK constraint is satisfied
        # during execution. The row is updated with final results after completion.
        preliminary_run = {
            "id": run_id,
            "tenant_id": input_payload.get("tenant_id", self.settings.default_tenant_id),
            "user_id": input_payload.get("user_id", "anonymous"),
            "domain_id": agent.domain,
            "agent_id": agent.agent_id,
            "status": "running",
            "input_payload": input_payload,
            "resolved_plan": plan.model_dump(),
            "final_output": None,
            "error_message": None,
            "token_usage": {},
            "cost_estimate": 0.0,
            "model": None,
            "started_at": started_at,
            "completed_at": None,
            "created_at": started_at,
            "updated_at": started_at,
        }
        if loop_context is not None:
            preliminary_run["loop_id"] = loop_context.loop_id
            preliminary_run["iteration_index"] = loop_context.iteration_index
        self.repository.save_run(preliminary_run)

        execution: dict[str, Any] | None = None
        try:
            if use_tool_loop:
                run_registry = build_run_registry(self.tool_registry, iv_tools, str(iv_run_id), self.settings)
                execution = run_tool_loop(
                    agent, input_payload,
                    ToolExecutor(run_registry, self.repository),
                    run_id, iv_tools,
                    model_override=model_override,
                    max_steps=max_steps or self.settings.neuroagent_default_max_steps,
                    max_tokens=max_tokens,
                    settings=self.settings,
                )
            else:
                execution = self.executor.execute(
                    run_id, agent, plan, input_payload,
                    model_override=model_override,
                    loop_context=loop_context,
                    max_steps=max_steps,
                    max_tokens=max_tokens,
                )
            status = execution.get("status", "completed")
            error_message = execution.get("error_message")
            if status == "completed":
                try:
                    validate_payload(agent.output_schema, execution["final_output"], "agent output")
                except Exception as exc:
                    execution["final_output"] = None
                    status = "failed"
                    error_message = str(exc)
        except Exception as exc:
            if execution is None:
                execution = {
                    "steps": [],
                    "tool_calls": [],
                    "final_output": None,
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0},
                    "cost_estimate": 0.0,
                    "model": None,
                }
            else:
                execution["final_output"] = None
            status = "failed"
            error_message = str(exc)
        completed_at = datetime.now(UTC).isoformat()

        # Build structured result
        result_status = self._map_result_status(status)
        run_result = self._build_run_result(
            result_status, execution, agent_id, loop_context,
        )

        run = {
            "id": run_id,
            "tenant_id": input_payload.get("tenant_id", self.settings.default_tenant_id),
            "user_id": input_payload.get("user_id", "anonymous"),
            "domain_id": agent.domain,
            "agent_id": agent.agent_id,
            "status": status,
            "input_payload": input_payload,
            "resolved_plan": plan.model_dump(),
            "final_output": execution["final_output"],
            "error_message": error_message,
            "token_usage": execution["token_usage"],
            "cost_estimate": execution["cost_estimate"],
            "model": execution["model"],
            "started_at": started_at,
            "completed_at": completed_at,
            "created_at": started_at,
            "updated_at": completed_at,
            "result": run_result.model_dump(),
        }

        # Echo loop context for correlation
        if loop_context is not None:
            run["loop_id"] = loop_context.loop_id
            run["iteration_index"] = loop_context.iteration_index

        self.repository.save_run(run)
        for step in execution["steps"]:
            self.repository.save_step(step)

        persisted_run = self.repository.get_run(run_id)
        if persisted_run is None:
            raise RuntimeError(f"Run {run_id} was not persisted")

        trace = self.artifacts.build_run_trace(persisted_run).model_dump()
        trace["run_id"] = run_id
        self.repository.save_artifact(trace)

        persisted_with_artifacts = self.repository.get_run(run_id)
        if persisted_with_artifacts is None:
            raise RuntimeError(f"Run {run_id} was not persisted")

        for result in self.evals.evaluate(agent, persisted_with_artifacts):
            evaluation = result.model_dump()
            evaluation["run_id"] = run_id
            self.repository.save_evaluation(evaluation)

        final_run = self.repository.get_run(run_id)
        if final_run is None:
            raise RuntimeError(f"Run {run_id} was not persisted")
        return final_run

    def _map_result_status(self, status: str) -> str:
        if status in {"completed"}:
            return "completed"
        if status in {"max_steps"}:
            return "max_steps"
        if status in {"max_tokens"}:
            return "max_tokens"
        return "error"

    def _build_run_result(
        self,
        result_status: str,
        execution: dict[str, Any],
        agent_id: str,
        loop_context: LoopContext | None,
    ) -> RunResult:
        token_usage = execution.get("token_usage", {})
        steps = execution.get("steps", [])
        tool_calls_raw = execution.get("tool_calls", [])

        # Aggregate tool calls by tool name
        tool_counter: Counter[str] = Counter()
        for tc in tool_calls_raw:
            tool_name = tc.get("tool_id") or tc.get("tool") or "unknown"
            tool_counter[tool_name] += 1
        tool_call_summaries = [ToolCallSummary(tool=t, count=c) for t, c in tool_counter.items()]

        # Build artifacts from steps that have output with artifact-like data
        artifacts: list[ArtifactRef] = []
        for step in steps:
            output = step.get("output_payload") or {}
            if isinstance(output, dict) and output.get("artifact_type"):
                artifacts.append(ArtifactRef(
                    type=output["artifact_type"],
                    ref=output.get("artifact_ref", ""),
                    description=output.get("artifact_description", ""),
                ))

        usage = UsageInfo(
            prompt_tokens=token_usage.get("prompt_tokens", 0),
            completion_tokens=token_usage.get("completion_tokens", 0),
            steps=len(steps),
        )

        # Generate summary via cheap model call (skip if errored before any step)
        summary = ""
        final_output = execution.get("final_output")
        if result_status != "error" and steps:
            try:
                summary = complete_simple(
                    system_prompt="Summarize what was accomplished in this agent run in 3-5 sentences. Be concise and factual.",
                    user_prompt=f"Agent: {agent_id}\nSteps completed: {len(steps)}\nFinal output: {str(final_output)[:1000]}",
                )
            except Exception:
                summary = ""

        final_answer = None
        if final_output is not None:
            final_answer = str(final_output) if not isinstance(final_output, str) else final_output

        return RunResult(
            status=result_status,  # type: ignore[arg-type]
            final_answer=final_answer,
            summary=summary,
            artifacts=artifacts,
            tool_calls=tool_call_summaries,
            usage=usage,
        )
