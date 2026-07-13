from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


RiskLevel = Literal["low", "medium", "high", "critical"]


class JsonSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str = "object"
    required: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)


class AgentContract(BaseModel):
    model_config = ConfigDict(extra="allow")

    agent_id: str
    name: str
    version: str
    domain: str

    @field_validator("version", mode="before")
    @classmethod
    def coerce_version_to_str(cls, v: object) -> str:
        return str(v)
    risk_level: RiskLevel = "low"
    role: str
    goal: str
    input_schema: JsonSchema
    output_schema: JsonSchema
    allowed_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    human_approval_required_for: list[str] = Field(default_factory=list)
    evaluation: list[str] = Field(default_factory=list)
