import app.evals.llm_judge as llm_judge
from app.contracts.agent_contract import AgentContract
from app.evals.llm_judge import judge_run


def _agent() -> AgentContract:
    return AgentContract.model_validate(
        {
            "agent_id": "research.test_agent",
            "name": "Test Agent",
            "version": "0.1.0",
            "domain": "research",
            "role": "Research role",
            "goal": "Produce a well-grounded research summary.",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
        }
    )


def _run() -> dict:
    return {
        "id": "run-1",
        "agent_id": "research.test_agent",
        "status": "completed",
        "input_payload": {"messages": [{"role": "user", "content": "Summarize X"}]},
        "final_output": {"summary": "A grounded summary of X."},
    }


def test_judge_parses_scored_verdict(monkeypatch) -> None:
    monkeypatch.setattr(
        llm_judge,
        "complete_simple",
        lambda system, user, settings=None: '{"score": 0.9, "passed": true, "critique": "Clear and grounded."}',
    )
    outcome = judge_run(_agent(), _run())
    assert outcome.passed is True
    assert outcome.score == 0.9
    assert "Clear and grounded." in outcome.findings[0]


def test_judge_extracts_json_from_fenced_and_prose(monkeypatch) -> None:
    monkeypatch.setattr(
        llm_judge,
        "complete_simple",
        lambda system, user, settings=None: 'Here is my verdict:\n```json\n{"score": 0.4, "passed": false, "critique": "Too shallow."}\n```',
    )
    outcome = judge_run(_agent(), _run())
    assert outcome.passed is False
    assert outcome.score == 0.4
    assert "Too shallow." in outcome.findings[0]


def test_judge_infers_pass_from_score_when_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        llm_judge,
        "complete_simple",
        lambda system, user, settings=None: '{"score": 0.8, "critique": "Good."}',
    )
    outcome = judge_run(_agent(), _run())
    assert outcome.passed is True  # 0.8 >= threshold


def test_judge_is_inconclusive_on_unparseable_output(monkeypatch) -> None:
    monkeypatch.setattr(
        llm_judge,
        "complete_simple",
        lambda system, user, settings=None: "not json at all",
    )
    outcome = judge_run(_agent(), _run())
    assert outcome.passed is False
    assert outcome.score == 0.5


def test_judge_never_raises_on_model_error(monkeypatch) -> None:
    def _boom(system, user, settings=None):
        raise RuntimeError("model down")

    monkeypatch.setattr(llm_judge, "complete_simple", _boom)
    outcome = judge_run(_agent(), _run())
    assert outcome.score == 0.5
    assert "model down" in outcome.findings[0]


def test_judge_uses_custom_rubric(monkeypatch) -> None:
    captured = {}

    def _capture(system, user, settings=None):
        captured["user"] = user
        return '{"score": 1.0, "passed": true, "critique": "ok"}'

    monkeypatch.setattr(llm_judge, "complete_simple", _capture)
    judge_run(_agent(), _run(), rubric="Must cite three sources.")
    assert "Must cite three sources." in captured["user"]
