from typing import Any

from app.contracts.agent_contract import AgentContract
from app.contracts.workflow_contract import ExecutionPlan
from app.core.runtime import AgentRuntime
from app.db.repositories import InMemoryRepository
from app.domains.registry import DomainRegistry
from app.model_gateway import ModelResponse
from app.tools.registry import ToolRegistry


class InvalidOutputGateway:
    def complete(
        self,
        agent: AgentContract,
        plan: ExecutionPlan,
        input_payload: dict[str, Any],
        findings: list[str],
    ) -> ModelResponse:
        return ModelResponse(
            content={"summary": "missing required fields"},
            token_usage={"prompt_tokens": 3, "completion_tokens": 2},
            cost_estimate=0.01,
            model="invalid-output-test",
        )


def test_stub_model_gateway_produces_output_matching_research_contract() -> None:
    repo = InMemoryRepository()
    run = AgentRuntime(
        DomainRegistry.from_default_path(),
        ToolRegistry.from_default_path(),
        repo,
    ).run_agent("research.literature_researcher", {"research_question": "governed agents"})

    assert run["status"] == "completed"
    assert run["final_output"]["summary"]
    assert isinstance(run["final_output"]["evidence"], list)
    assert isinstance(run["final_output"]["confidence_score"], float)


def test_stub_model_gateway_produces_sigma_specific_required_fields() -> None:
    repo = InMemoryRepository()
    run = AgentRuntime(
        DomainRegistry.from_default_path(),
        ToolRegistry.from_default_path(),
        repo,
    ).run_agent(
        "cybersecurity.sigma_rule_agent",
        {"threat_description": "encoded PowerShell", "target_platform": "windows"},
    )

    assert run["status"] == "completed"
    assert run["final_output"]["sigma_rule"]["logsource"]["product"] == "windows"
    assert run["final_output"]["false_positive_analysis"]


def test_runtime_records_model_usage_and_cost_from_gateway() -> None:
    repo = InMemoryRepository()
    run = AgentRuntime(
        DomainRegistry.from_default_path(),
        ToolRegistry.from_default_path(),
        repo,
    ).run_agent("research.literature_researcher", {"research_question": "governed agents"})

    assert run["model"] == "stub-model"
    assert run["token_usage"]["prompt_tokens"] > 0
    assert run["token_usage"]["completion_tokens"] > 0
    assert run["cost_estimate"] > 0


def test_runtime_marks_run_failed_when_model_output_violates_contract() -> None:
    repo = InMemoryRepository()
    run = AgentRuntime(
        DomainRegistry.from_default_path(),
        ToolRegistry.from_default_path(),
        repo,
        model_gateway=InvalidOutputGateway(),
    ).run_agent("research.literature_researcher", {"research_question": "governed agents"})

    assert run["status"] == "failed"
    assert run["final_output"] is None
    assert "confidence_score" in run["error_message"]


def test_failed_run_is_persisted_with_trace_artifact_and_evaluations() -> None:
    repo = InMemoryRepository()
    run = AgentRuntime(
        DomainRegistry.from_default_path(),
        ToolRegistry.from_default_path(),
        repo,
        model_gateway=InvalidOutputGateway(),
    ).run_agent("research.literature_researcher", {"research_question": "governed agents"})

    persisted = repo.get_run(run["id"])
    assert persisted is not None
    assert persisted["status"] == "failed"
    assert persisted["artifacts"][0]["name"] == "run_trace.json"
    assert persisted["evaluations"]
