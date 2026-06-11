import pytest

from app.core.errors import ApprovalRequiredError, ToolPolicyError
from app.domains.registry import DomainRegistry
from app.tools.policy import ToolPolicy
from app.tools.registry import ToolRegistry


def test_forbidden_tool_is_blocked() -> None:
    agent = DomainRegistry.from_default_path().get_agent("cybersecurity.sigma_rule_agent")
    tool = ToolRegistry.from_default_path().get("shell.execute")
    with pytest.raises(ToolPolicyError):
        ToolPolicy().validate(agent, tool)


def test_high_risk_tool_requires_approval_when_allowed() -> None:
    agent = DomainRegistry.from_default_path().get_agent("research.literature_researcher").model_copy(
        update={"allowed_tools": ["shell.execute"], "forbidden_tools": []}
    )
    tool = ToolRegistry.from_default_path().get("shell.execute")
    with pytest.raises(ApprovalRequiredError):
        ToolPolicy().validate(agent, tool)
