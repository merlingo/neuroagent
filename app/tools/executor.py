from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from app.contracts.agent_contract import AgentContract
from app.core.approvals import ApprovalGate
from app.core.errors import ApprovalRequiredError
from app.db.repositories import Repository
from app.tools.policy import ToolPolicy
from app.tools.registry import ToolRegistry


class ToolExecutor:
    def __init__(self, registry: ToolRegistry, repository: Repository) -> None:
        self.registry = registry
        self.repository = repository
        self.policy = ToolPolicy()
        self.approvals = ApprovalGate()

    def execute(
        self,
        run_id: str,
        agent: AgentContract,
        tool_id: str,
        payload: dict,
        step_id: str | None = None,
    ) -> dict:
        tool_contract = self.registry.get(tool_id)
        started = perf_counter()
        try:
            self.policy.validate(agent, tool_contract)
            output = self.registry.run(tool_id, payload)
            approval_status = "not_required"
            error = None
        except ApprovalRequiredError as exc:
            approval = self.approvals.create(run_id, tool_id, str(exc))
            self.repository.save_approval(approval.__dict__)
            output = {"approval_request_id": approval.id, "status": "pending_approval"}
            approval_status = "pending"
            error = None
        latency_ms = int((perf_counter() - started) * 1000)
        call = {
            "id": str(uuid4()),
            "run_id": run_id,
            "step_id": step_id,
            "tool_name": tool_id,
            "tool_version": tool_contract.version,
            "input_payload": payload,
            "output_payload": output,
            "risk_level": tool_contract.risk_level,
            "approval_required": tool_contract.requires_approval,
            "approval_status": approval_status,
            "latency_ms": latency_ms,
            "error_message": error,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repository.save_tool_call(call)
        return call
