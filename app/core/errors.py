class NeuroAgentError(Exception):
    """Base framework exception."""


class ContractNotFoundError(NeuroAgentError):
    """Raised when a requested contract is missing."""


class ToolPolicyError(NeuroAgentError):
    """Raised when tool execution violates policy."""


class ApprovalRequiredError(NeuroAgentError):
    """Raised when a tool must wait for human approval."""


class ContractValidationError(NeuroAgentError):
    """Raised when payloads fail a contract schema check."""
