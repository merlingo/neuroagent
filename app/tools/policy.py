from app.contracts.agent_contract import AgentContract
from app.contracts.tool_contract import ToolContract
from app.core.errors import ApprovalRequiredError, ToolPolicyError


class ToolPolicy:
    def validate(self, agent: AgentContract, tool: ToolContract) -> None:
        if tool.tool_id in agent.forbidden_tools:
            raise ToolPolicyError(f"Tool {tool.tool_id} is forbidden for {agent.agent_id}")
        if agent.allowed_tools and tool.tool_id not in agent.allowed_tools:
            raise ToolPolicyError(f"Tool {tool.tool_id} is not allowlisted for {agent.agent_id}")
        if tool.allowed_domains and agent.domain not in tool.allowed_domains:
            raise ToolPolicyError(f"Tool {tool.tool_id} is not allowed for domain {agent.domain}")
        if tool.requires_approval or tool.risk_level in {"high", "critical"}:
            raise ApprovalRequiredError(f"Tool {tool.tool_id} requires human approval")
