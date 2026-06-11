from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api.routes_approvals import approve, pending_approvals, reject
from app.contracts.validation import validate_payload
from app.core.errors import ContractValidationError
from app.core.runtime import AgentRuntime
from app.db.repositories import InMemoryRepository, repository
from app.domains.registry import DomainRegistry
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry


def test_validate_payload_accepts_required_string_fields() -> None:
    agent = DomainRegistry.from_default_path().get_agent("cybersecurity.sigma_rule_agent")
    validate_payload(
        agent.input_schema,
        {"threat_description": "encoded PowerShell", "target_platform": "windows"},
        "agent input",
    )


def test_validate_payload_rejects_missing_required_field() -> None:
    agent = DomainRegistry.from_default_path().get_agent("cybersecurity.sigma_rule_agent")
    with pytest.raises(ContractValidationError, match="target_platform"):
        validate_payload(agent.input_schema, {"threat_description": "encoded PowerShell"}, "agent input")


def test_validate_payload_rejects_wrong_field_type() -> None:
    agent = DomainRegistry.from_default_path().get_agent("cybersecurity.sigma_rule_agent")
    with pytest.raises(ContractValidationError, match="target_platform must be string"):
        validate_payload(
            agent.input_schema,
            {"threat_description": "encoded PowerShell", "target_platform": 7},
            "agent input",
        )


def test_runtime_rejects_invalid_agent_input_before_creating_run() -> None:
    repo = InMemoryRepository()
    runtime = AgentRuntime(DomainRegistry.from_default_path(), ToolRegistry.from_default_path(), repo)
    with pytest.raises(ContractValidationError):
        runtime.run_agent("research.literature_researcher", {"topic": "wrong field"})
    assert repo.runs == {}


def test_approval_routes_list_approve_and_reject_requests() -> None:
    repository.approvals.clear()
    repository.save_approval(
        {"id": "approval-1", "run_id": "run-1", "tool_id": "shell.execute", "reason": "risk", "status": "pending"}
    )
    repository.save_approval(
        {"id": "approval-2", "run_id": "run-1", "tool_id": "email.send", "reason": "risk", "status": "pending"}
    )

    assert [approval["id"] for approval in pending_approvals()] == ["approval-1", "approval-2"]
    assert approve("approval-1")["status"] == "approved"
    assert reject("approval-2")["status"] == "rejected"
    assert pending_approvals() == []


def test_approval_route_raises_404_for_missing_request() -> None:
    with pytest.raises(HTTPException) as exc:
        approve("missing")
    assert exc.value.status_code == 404


def test_tool_executor_stores_pending_approval_in_repository() -> None:
    repo = InMemoryRepository()
    agent = DomainRegistry.from_default_path().get_agent("research.literature_researcher").model_copy(
        update={"allowed_tools": ["shell.execute"], "forbidden_tools": []}
    )
    ToolExecutor(ToolRegistry.from_default_path(), repo).execute(
        run_id="run-123",
        agent=agent,
        tool_id="shell.execute",
        payload={"command": "date"},
    )
    assert repo.list_pending_approvals()[0]["run_id"] == "run-123"


def test_sqlalchemy_models_include_blueprint_required_tables() -> None:
    model_source = Path("app/db/models.py").read_text()
    expected_tables = {
        "tenants",
        "users",
        "domain_stacks",
        "agent_definitions",
        "prompt_templates",
        "tool_definitions",
        "tool_policies",
        "agent_runs",
        "agent_steps",
        "tool_calls",
        "artifacts",
        "documents",
        "document_chunks",
        "embedding_records",
        "evaluation_runs",
        "evaluation_results",
        "approval_requests",
        "audit_logs",
        "obsidian_note_records",
    }
    for table_name in expected_tables:
        assert f'__tablename__ = "{table_name}"' in model_source
