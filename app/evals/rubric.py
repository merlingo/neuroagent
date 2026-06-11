from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_RUBRIC = "Outputs must be structured, traceable, and policy-compliant."


@dataclass(frozen=True)
class EvalOutcome:
    passed: bool
    score: float
    rubric: str
    findings: list[str] = field(default_factory=list)


def passed(rubric: str, findings: list[str] | None = None, score: float = 1.0) -> EvalOutcome:
    return EvalOutcome(True, _bounded(score), rubric, findings or [])


def failed(rubric: str, findings: list[str] | None = None, score: float = 0.0) -> EvalOutcome:
    return EvalOutcome(False, _bounded(score), rubric, findings or [])


def _bounded(score: float) -> float:
    return round(max(0.0, min(1.0, score)), 3)
