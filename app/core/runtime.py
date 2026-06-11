from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.contracts.validation import validate_payload
from app.core.artifacts import ArtifactWriter
from app.core.executor import StepExecutor
from app.core.planner import SimplePlanner
from app.db.repositories import Repository
from app.domains.registry import DomainRegistry
from app.evals.runner import EvaluationRunner
from app.model_gateway import ModelGateway, get_model_gateway
from app.settings import get_settings
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry


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

    def run_agent(self, agent_id: str, input_payload: dict[str, Any]) -> dict:
        agent = self.domain_registry.get_agent(agent_id)
        validate_payload(agent.input_schema, input_payload, "agent input")
        run_id = str(uuid4())
        started_at = datetime.now(UTC).isoformat()
        plan = self.planner.create_plan(agent)
        execution: dict[str, Any] | None = None
        try:
            execution = self.executor.execute(run_id, agent, plan, input_payload)
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
        }
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
