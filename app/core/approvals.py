from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class ApprovalRequest:
    id: str
    run_id: str
    tool_id: str
    reason: str
    status: str = "pending"


class ApprovalGate:
    def create(self, run_id: str, tool_id: str, reason: str) -> ApprovalRequest:
        return ApprovalRequest(id=str(uuid4()), run_id=run_id, tool_id=tool_id, reason=reason)
