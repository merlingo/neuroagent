from typing import Any

from pydantic import BaseModel, Field

from app.contracts.agent_contract import JsonSchema, RiskLevel


class ToolContract(BaseModel):
    tool_id: str
    name: str
    version: str
    risk_level: RiskLevel = "low"
    requires_approval: bool = False
    input_schema: JsonSchema = Field(default_factory=JsonSchema)
    output_schema: JsonSchema = Field(default_factory=JsonSchema)
    timeout_seconds: int = 30
    allowed_domains: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
