import pytest
from fastapi import HTTPException

from app.api.routes_agents import RunAgentRequest, run_agent
from app.api.routes_approvals import approve, reject
from app.contracts.agent_contract import JsonSchema
from app.contracts.validation import validate_payload
from app.core.errors import ContractValidationError
from app.db.repositories import InMemoryRepository
from app.main import app


def test_validate_payload_accepts_object_array_boolean_integer_and_number_types() -> None:
    schema = JsonSchema(
        type="object",
        required=["metadata", "items", "enabled", "count", "score"],
        properties={
            "metadata": {"type": "object"},
            "items": {"type": "array"},
            "enabled": {"type": "boolean"},
            "count": {"type": "integer"},
            "score": {"type": "number"},
        },
    )
    validate_payload(
        schema,
        {
            "metadata": {"source": "test"},
            "items": ["a", "b"],
            "enabled": True,
            "count": 2,
            "score": 0.8,
        },
        "payload",
    )


def test_validate_payload_rejects_bool_for_integer_schema() -> None:
    schema = JsonSchema(
        type="object",
        required=["count"],
        properties={"count": {"type": "integer"}},
    )
    with pytest.raises(ContractValidationError, match="payload.count must be integer"):
        validate_payload(schema, {"count": True}, "payload")


def test_validate_payload_rejects_bool_for_number_schema() -> None:
    schema = JsonSchema(
        type="object",
        required=["score"],
        properties={"score": {"type": "number"}},
    )
    with pytest.raises(ContractValidationError, match="payload.score must be number"):
        validate_payload(schema, {"score": False}, "payload")


def test_validate_payload_rejects_non_object_schema() -> None:
    schema = JsonSchema(type="array")
    with pytest.raises(ContractValidationError, match="schema type must be object"):
        validate_payload(schema, {}, "payload")


def test_validate_payload_ignores_unknown_json_schema_type_for_forward_compatibility() -> None:
    schema = JsonSchema(
        type="object",
        required=["custom"],
        properties={"custom": {"type": "date-time"}},
    )
    validate_payload(schema, {"custom": "2026-06-07T00:00:00Z"}, "payload")


def test_run_agent_route_translates_contract_validation_error_to_400() -> None:
    with pytest.raises(HTTPException) as exc:
        run_agent(
            "cybersecurity.sigma_rule_agent",
            RunAgentRequest(input_payload={"threat_description": "missing platform"}),
        )
    assert exc.value.status_code == 400
    assert "target_platform" in exc.value.detail


def test_approval_routes_are_registered_on_fastapi_app() -> None:
    paths = {route.path for route in app.routes}
    assert "/approvals/pending" in paths
    assert "/approvals/{approval_id}/approve" in paths
    assert "/approvals/{approval_id}/reject" in paths


def test_reject_route_raises_404_for_missing_approval_request() -> None:
    with pytest.raises(HTTPException) as exc:
        reject("missing-approval")
    assert exc.value.status_code == 404
    assert exc.value.detail == "Approval request not found"


def test_repository_update_approval_returns_none_for_missing_id() -> None:
    repo = InMemoryRepository()
    assert repo.update_approval("missing", "approved") is None


def test_repository_pending_approvals_filters_non_pending_statuses() -> None:
    repo = InMemoryRepository()
    repo.save_approval({"id": "a", "status": "pending"})
    repo.save_approval({"id": "b", "status": "approved"})
    repo.save_approval({"id": "c", "status": "rejected"})
    assert repo.list_pending_approvals() == [{"id": "a", "status": "pending"}]


def test_approval_status_can_transition_from_pending_to_approved() -> None:
    repo = InMemoryRepository()
    repo.save_approval({"id": "approval-1", "status": "pending"})
    assert repo.update_approval("approval-1", "approved") == {
        "id": "approval-1",
        "status": "approved",
    }


def test_approve_route_preserves_approval_metadata() -> None:
    from app.db.repositories import repository

    repository.approvals.clear()
    repository.save_approval(
        {
            "id": "approval-metadata",
            "run_id": "run-1",
            "tool_id": "shell.execute",
            "reason": "Tool shell.execute requires human approval",
            "status": "pending",
        }
    )
    approved = approve("approval-metadata")
    assert approved["status"] == "approved"
    assert approved["run_id"] == "run-1"
    assert approved["tool_id"] == "shell.execute"
