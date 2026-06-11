from __future__ import annotations

from collections.abc import Iterable

from app.contracts.agent_contract import AgentContract
from app.contracts.eval_contract import EvaluationResult
from app.evals.validators import VALIDATORS, unknown_evaluation


DEFAULT_EVALUATIONS = [
    "no_empty_answer",
    "output_schema_valid",
    "tool_policy_respected",
    "approval_rules_respected",
]


class EvaluationRunner:
    def evaluate(self, agent: AgentContract, run: dict) -> list[EvaluationResult]:
        results: list[EvaluationResult] = []
        for eval_name in _ordered_unique([*DEFAULT_EVALUATIONS, *agent.evaluation]):
            validator = VALIDATORS.get(eval_name) or unknown_evaluation(eval_name)
            outcome = validator(agent, run)
            results.append(
                EvaluationResult(
                    eval_name=eval_name,
                    passed=outcome.passed,
                    score=outcome.score,
                    rubric=outcome.rubric,
                    findings=outcome.findings,
                )
            )
        return results


def _ordered_unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        unique.append(value)
        seen.add(value)
    return unique
