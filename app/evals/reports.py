from __future__ import annotations

from collections import Counter
from typing import Any


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed_count = sum(1 for result in results if result.get("passed"))
    scores = [float(result.get("score", 1.0 if result.get("passed") else 0.0)) for result in results]
    failed_names = Counter(
        str(result.get("eval_name", result.get("name", "evaluation")))
        for result in results
        if not result.get("passed")
    )
    return {
        "total": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "pass_rate": round(passed_count / total, 3) if total else 1.0,
        "average_score": round(sum(scores) / total, 3) if total else 1.0,
        "failed_evaluations": dict(sorted(failed_names.items())),
    }


def build_report(runs: list[dict[str, Any]]) -> dict[str, Any]:
    evaluations = [
        evaluation
        for run in runs
        for evaluation in run.get("evaluations", [])
    ]
    return {
        "status": "ready",
        "runs": len(runs),
        "summary": summarize(evaluations),
    }
