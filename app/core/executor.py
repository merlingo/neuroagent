from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.contracts.agent_contract import AgentContract
from app.contracts.loop_contract import LoopContext
from app.contracts.workflow_contract import ExecutionPlan, WorkflowStep
from app.model_gateway import ModelGateway, StubModelGateway
from app.tools.executor import ToolExecutor


class StepExecutor:
    def __init__(self, tool_executor: ToolExecutor, model_gateway: ModelGateway | None = None) -> None:
        self.tool_executor = tool_executor
        self.model_gateway = model_gateway or StubModelGateway()

    def execute(
        self,
        run_id: str,
        agent: AgentContract,
        plan: ExecutionPlan,
        payload: dict[str, Any],
        *,
        model_override: str | None = None,
        loop_context: LoopContext | None = None,
        max_steps: int | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        steps: list[dict] = []
        tool_calls: list[dict] = []
        step_outputs: dict[str, Any] = {}
        findings = [f"Validated input for {agent.agent_id}."]
        final_output: dict[str, Any] | None = None
        token_usage = {"prompt_tokens": 0, "completion_tokens": 0}
        cost_estimate = 0.0
        model: str | None = None

        cumulative_tokens = 0

        for index, step in enumerate(plan.steps):
            # Budget enforcement: max_steps
            if max_steps is not None and index >= max_steps:
                return {
                    "status": "max_steps",
                    "error_message": None,
                    "steps": steps,
                    "tool_calls": tool_calls,
                    "final_output": final_output,
                    "token_usage": token_usage,
                    "cost_estimate": cost_estimate,
                    "model": model,
                }
            # Budget enforcement: max_tokens
            if max_tokens is not None and cumulative_tokens >= max_tokens:
                return {
                    "status": "max_tokens",
                    "error_message": None,
                    "steps": steps,
                    "tool_calls": tool_calls,
                    "final_output": final_output,
                    "token_usage": token_usage,
                    "cost_estimate": cost_estimate,
                    "model": model,
                }

            started_at = datetime.now(UTC).isoformat()
            trace_input = self._build_trace_input(step, payload, step_outputs)
            status = "completed"
            error_message = None
            output: dict[str, Any] | None

            try:
                if step.type == "tool_call" and step.tool:
                    tool_payload = self._build_tool_payload(step, run_id, payload, step_outputs, findings)
                    result = self.tool_executor.execute(
                        run_id=run_id,
                        agent=agent,
                        tool_id=step.tool,
                        payload=tool_payload,
                        step_id=step.step_id,
                    )
                    tool_calls.append(result)
                    output = result
                    if result.get("approval_status") == "pending":
                        status = "pending_approval"
                elif step.type == "agent_reasoning" and self._is_final_output_step(step):
                    model_response = self.model_gateway.complete(
                        agent, plan, payload, findings,
                        model_override=model_override, loop_context=loop_context,
                    )
                    final_output = model_response.content
                    token_usage = model_response.token_usage
                    cost_estimate = model_response.cost_estimate
                    model = model_response.model
                    cumulative_tokens += token_usage.get("prompt_tokens", 0) + token_usage.get("completion_tokens", 0)
                    output = {
                        "final_output": final_output,
                        "token_usage": token_usage,
                        "cost_estimate": cost_estimate,
                        "model": model,
                    }
                else:
                    output = self._reasoning_output(step, trace_input, findings)
            except Exception as exc:
                output = None
                status = "failed"
                error_message = str(exc)

            completed_at = datetime.now(UTC).isoformat()
            step_record = {
                "id": str(uuid4()),
                "run_id": run_id,
                "step_index": index,
                "step_id": step.step_id,
                "name": step.step_id,
                "step_type": step.type,
                "input_payload": trace_input,
                "status": status,
                "output_payload": output,
                "error_message": error_message,
                "started_at": started_at,
                "completed_at": completed_at,
            }
            steps.append(step_record)
            step_outputs[step.step_id] = output

            if output is not None:
                findings.append(self._summarize_step_output(step.step_id, output))
            if status in {"failed", "pending_approval"}:
                return {
                    "status": status,
                    "error_message": error_message,
                    "steps": steps,
                    "tool_calls": tool_calls,
                    "final_output": final_output,
                    "token_usage": token_usage,
                    "cost_estimate": cost_estimate,
                    "model": model,
                }

        if final_output is None:
            model_response = self.model_gateway.complete(
                agent, plan, payload, findings,
                model_override=model_override, loop_context=loop_context,
            )
            final_output = model_response.content
            token_usage = model_response.token_usage
            cost_estimate = model_response.cost_estimate
            model = model_response.model

        return {
            "status": "completed",
            "error_message": None,
            "steps": steps,
            "tool_calls": tool_calls,
            "final_output": final_output,
            "token_usage": token_usage,
            "cost_estimate": cost_estimate,
            "model": model,
        }

    def _build_trace_input(
        self,
        step: WorkflowStep,
        original_payload: dict[str, Any],
        step_outputs: dict[str, Any],
    ) -> dict[str, Any]:
        dependency_outputs = self._dependency_outputs(step, step_outputs)
        trace_input: dict[str, Any] = {
            "original_input": original_payload,
            "step_input": step.input,
        }
        if dependency_outputs:
            trace_input["dependency_outputs"] = dependency_outputs
        previous_output = self._previous_output(step_outputs)
        if previous_output is not None:
            trace_input["previous_step_output"] = previous_output
        return trace_input

    def _build_tool_payload(
        self,
        step: WorkflowStep,
        run_id: str,
        original_payload: dict[str, Any],
        step_outputs: dict[str, Any],
        findings: list[str],
    ) -> dict[str, Any]:
        if step.input:
            return dict(step.input)
        dependency_outputs = self._dependency_outputs(step, step_outputs)
        previous_output = self._previous_output(step_outputs)
        context_output = dependency_outputs or previous_output or original_payload
        if step.tool == "obsidian.write_note":
            return {
                "title": f"Agent Run {run_id}",
                "body": self._note_body(context_output, findings),
                "context": context_output,
            }
        if isinstance(context_output, dict):
            return context_output
        return {"value": context_output}

    def _reasoning_output(
        self,
        step: WorkflowStep,
        trace_input: dict[str, Any],
        findings: list[str],
    ) -> dict[str, Any]:
        return {
            "summary": f"Completed reasoning step {step.step_id}.",
            "findings": list(findings),
            "available_context": sorted(trace_input.keys()),
        }

    def _dependency_outputs(self, step: WorkflowStep, step_outputs: dict[str, Any]) -> dict[str, Any]:
        return {
            dependency: step_outputs[dependency]
            for dependency in step.depends_on
            if dependency in step_outputs
        }

    def _previous_output(self, step_outputs: dict[str, Any]) -> Any:
        if not step_outputs:
            return None
        return next(reversed(step_outputs.values()))

    def _is_final_output_step(self, step: WorkflowStep) -> bool:
        return step.step_id == "produce_output"

    def _summarize_step_output(self, step_id: str, output: dict[str, Any]) -> str:
        return f"Step {step_id} produced: {output}"

    def _note_body(self, context_output: Any, findings: list[str]) -> str:
        return "\n\n".join(
            [
                "Findings:",
                "\n".join(f"- {finding}" for finding in findings),
                "Context:",
                str(context_output),
            ]
        )
