from typing import Any

from app.contracts.agent_contract import AgentContract
from app.contracts.workflow_contract import ExecutionPlan
from app.core.runtime import AgentRuntime
from app.db.repositories import InMemoryRepository
from app.domains.registry import DomainRegistry
from app.model_gateway import ModelResponse
from app.tools.registry import ToolRegistry


class CountingGateway:
    def __init__(self) -> None:
        self.calls = 0

    def complete(
        self,
        agent: AgentContract,
        plan: ExecutionPlan,
        input_payload: dict[str, Any],
        findings: list[str],
        **kwargs: Any,
    ) -> ModelResponse:
        self.calls += 1
        return ModelResponse(
            content={"summary": "single model call", "evidence": [], "confidence_score": 0.82},
            token_usage={"prompt_tokens": 11, "completion_tokens": 7},
            cost_estimate=0.000018,
            model="counting-test",
        )


def test_step_executor_calls_model_once_and_uses_output_as_later_tool_context() -> None:
    repo = InMemoryRepository()
    gateway = CountingGateway()
    run = AgentRuntime(
        DomainRegistry.from_default_path(),
        ToolRegistry.from_default_path(),
        repo,
        model_gateway=gateway,
    ).run_agent("research.literature_researcher", {"research_question": "executor flow"})

    assert run["status"] == "completed"
    assert gateway.calls == 1
    assert run["model"] == "counting-test"

    tool_call = repo.list_run_tool_calls(run["id"])[0]
    context = tool_call["input_payload"]["context"]
    assert context["produce_output"]["final_output"] == run["final_output"]


def test_step_executor_records_dependency_outputs_in_step_trace() -> None:
    repo = InMemoryRepository()
    run = AgentRuntime(
        DomainRegistry.from_default_path(),
        ToolRegistry.from_default_path(),
        repo,
        model_gateway=CountingGateway(),
    ).run_agent("research.literature_researcher", {"research_question": "executor flow"})

    steps = repo.list_run_steps(run["id"])
    produce_output = next(step for step in steps if step["step_id"] == "produce_output")
    write_note = next(step for step in steps if step["step_id"] == "write_obsidian_note")

    assert "understand_request" in produce_output["input_payload"]["dependency_outputs"]
    assert "produce_output" in write_note["input_payload"]["dependency_outputs"]
    assert write_note["status"] == "completed"
