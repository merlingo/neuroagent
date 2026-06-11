from typing import Any, Literal

from pydantic import BaseModel, Field


class WorkflowStep(BaseModel):
    step_id: str
    type: Literal["tool_call", "agent_reasoning", "workflow"]
    input: dict[str, Any] = Field(default_factory=dict)
    tool: str | None = None
    approval_required: bool = False
    depends_on: list[str] = Field(default_factory=list)


class ExecutionPlan(BaseModel):
    intent: str
    domain: str
    agent_id: str
    steps: list[WorkflowStep]
    approval_points: list[str] = Field(default_factory=list)
    expected_artifacts: list[str] = Field(default_factory=list)


class WorkflowContract(BaseModel):
    workflow_id: str
    name: str
    version: str
    domain: str
    steps: list[WorkflowStep]
