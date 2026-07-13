from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RiskPolicy(BaseModel):
    model_config = ConfigDict(extra="allow")

    default_tool_risk: Literal["low", "medium", "high", "critical"] = "medium"
    require_approval_for: list[str] = Field(default_factory=list)


class DomainContract(BaseModel):
    model_config = ConfigDict(extra="allow")

    domain_id: str
    name: str
    version: str
    status: Literal["experimental", "active", "deprecated"] = "experimental"
    supported_tasks: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    default_memory_scope: list[str] = Field(default_factory=lambda: ["tenant", "domain"])
    risk_policy: RiskPolicy = Field(default_factory=RiskPolicy)
