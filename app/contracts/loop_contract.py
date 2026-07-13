from typing import Literal

from pydantic import BaseModel, Field


class LoopContext(BaseModel):
    loop_id: str
    iteration_index: int
    goal: str
    state_document: str
    prior_summaries: list[str] = Field(default_factory=list)


class ArtifactRef(BaseModel):
    type: str
    ref: str
    description: str


class ToolCallSummary(BaseModel):
    tool: str
    count: int


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    steps: int = 0


class RunResult(BaseModel):
    status: Literal["completed", "max_steps", "max_tokens", "error"]
    final_answer: str | None = None
    summary: str = ""
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    tool_calls: list[ToolCallSummary] = Field(default_factory=list)
    usage: UsageInfo = Field(default_factory=UsageInfo)


class EvaluateRequest(BaseModel):
    goal: str
    state_document: str
    iteration_summary: str
    recent_verdicts: list[str] = Field(default_factory=list)
    model: str | None = None


class EvaluateResponse(BaseModel):
    progress: Literal["advanced", "partial", "none"]
    confidence: float = Field(ge=0.0, le=1.0)
    stall_signals: list[str] = Field(default_factory=list)
    recommendation: Literal["continue", "checkpoint", "stop"]
    reasoning: str
