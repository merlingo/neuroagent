from typing import Any, Literal

from pydantic import BaseModel, Field


MeasurableAssetType = Literal[
    "agent_contract",
    "prompt_template",
    "tool_policy",
    "eval_rubric",
    "domain_contract",
]


class DomainMeasurement(BaseModel):
    name: str
    description: str
    higher_is_better: bool = True
    baseline: float | None = None
    target: float | None = None


class DomainImprovementTarget(BaseModel):
    asset_type: MeasurableAssetType
    asset_id: str
    path: str
    objective: str
    measurements: list[DomainMeasurement] = Field(default_factory=list)


class AutoresearchExperimentPlan(BaseModel):
    domain_id: str
    budget_minutes: int
    editable_targets: list[DomainImprovementTarget]
    fixed_context: list[str] = Field(default_factory=list)
    primary_metric: str
    acceptance_rule: str
    program_markdown: str
    artifacts: dict[str, str | dict | list]


class AutoresearchAssetSnapshot(BaseModel):
    target: DomainImprovementTarget
    exists: bool
    content_hash: str | None = None
    size_bytes: int = 0
    summary: str


class AutoresearchMeasurementResult(BaseModel):
    name: str
    score: float
    passed: bool
    higher_is_better: bool = True
    baseline: float | None = None
    target: float | None = None
    finding: str


KeepDecision = Literal["keep", "discard", "needs_review"]


class AutoresearchKeepDecision(BaseModel):
    decision: KeepDecision
    primary_metric: str
    baseline: float | None = None
    score: float | None = None
    delta: float | None = None
    reason: str


class AutoresearchImprovementRun(BaseModel):
    run_id: str
    domain_id: str
    status: Literal["completed", "failed"] = "completed"
    plan: AutoresearchExperimentPlan
    asset_snapshots: list[AutoresearchAssetSnapshot]
    measurement_results: list[AutoresearchMeasurementResult]
    keep_decision: AutoresearchKeepDecision
    artifacts: dict[str, str | dict[str, Any] | list[Any]]
