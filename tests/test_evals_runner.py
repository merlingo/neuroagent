from app.contracts.agent_contract import AgentContract
from app.evals.reports import build_report
from app.evals.runner import EvaluationRunner


def _agent(evaluation: list[str] | None = None) -> AgentContract:
    return AgentContract.model_validate(
        {
            "agent_id": "research.test_agent",
            "name": "Test Agent",
            "version": "0.1.0",
            "domain": "research",
            "role": "Research role",
            "goal": "Research goal",
            "input_schema": {"type": "object"},
            "output_schema": {
                "type": "object",
                "required": ["summary", "evidence", "confidence_score"],
                "properties": {
                    "summary": {"type": "string"},
                    "evidence": {"type": "array"},
                    "confidence_score": {"type": "number"},
                },
            },
            "allowed_tools": ["rag.search"],
            "forbidden_tools": ["shell.execute"],
            "evaluation": evaluation or [],
        }
    )


def _run(**updates: object) -> dict:
    run = {
        "id": "run-1",
        "status": "completed",
        "final_output": {
            "summary": "Claim with limitations and assumptions.",
            "evidence": [{"source": "doc-1", "quote": "evidence"}],
            "confidence_score": 0.8,
        },
        "tool_calls": [],
        "error_message": None,
    }
    run.update(updates)
    return run


def _by_name(results: list) -> dict:
    return {result.eval_name: result for result in results}


def test_evaluation_runner_applies_default_and_agent_checks() -> None:
    results = _by_name(EvaluationRunner().evaluate(_agent(["claims_have_evidence", "limitations_present"]), _run()))

    assert results["no_empty_answer"].passed
    assert results["output_schema_valid"].passed
    assert results["tool_policy_respected"].passed
    assert results["approval_rules_respected"].passed
    assert results["claims_have_evidence"].passed
    assert results["limitations_present"].passed


def test_evaluation_runner_fails_missing_output_and_schema() -> None:
    results = _by_name(EvaluationRunner().evaluate(_agent(), _run(status="failed", final_output=None)))

    assert not results["no_empty_answer"].passed
    assert not results["output_schema_valid"].passed
    assert results["no_empty_answer"].score == 0.0


def test_evaluation_runner_detects_policy_and_approval_violations() -> None:
    run = _run(
        tool_calls=[
            {
                "tool_name": "shell.execute",
                "approval_required": True,
                "approval_status": "not_required",
                "error_message": None,
            }
        ]
    )
    results = _by_name(EvaluationRunner().evaluate(_agent(), run))

    assert not results["tool_policy_respected"].passed
    assert not results["approval_rules_respected"].passed


def test_evaluation_runner_fails_unknown_eval_names() -> None:
    results = _by_name(EvaluationRunner().evaluate(_agent(["custom_unknown_eval"]), _run()))

    assert not results["custom_unknown_eval"].passed
    assert "No evaluator is registered" in results["custom_unknown_eval"].findings[0]


def test_eval_report_builds_repository_summary() -> None:
    report = build_report(
        [
            {
                "id": "run-1",
                "evaluations": [
                    {"eval_name": "a", "passed": True, "score": 1.0},
                    {"eval_name": "b", "passed": False, "score": 0.0},
                ],
            },
            {"id": "run-2", "evaluations": [{"eval_name": "a", "passed": True, "score": 0.5}]},
        ]
    )

    assert report["status"] == "ready"
    assert report["runs"] == 2
    assert report["summary"]["failed_evaluations"] == {"b": 1}
