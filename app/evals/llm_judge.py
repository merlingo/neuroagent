"""LLM-as-judge evaluation.

Deterministic validators (``app.evals.validators``) check structural policy
compliance. This module adds a qualitative judge: it hands the agent's final
output plus a rubric to an LLM and asks for a 0..1 score with a written
critique. It degrades gracefully — if the model is unavailable or returns an
unparseable answer, it yields a neutral, non-blocking outcome rather than
raising, so callers can always render *something*.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.contracts.agent_contract import AgentContract
from app.evals.rubric import DEFAULT_RUBRIC, EvalOutcome, _bounded
from app.model_gateway import complete_simple
from app.settings import Settings, get_settings


JUDGE_EVAL_NAME = "llm_judge"
_PASS_THRESHOLD = 0.6

_SYSTEM_PROMPT = (
    "You are a strict but fair evaluator of AI agent outputs. "
    "You grade an agent's final answer against its goal and a rubric. "
    "Respond ONLY with a JSON object of the form "
    '{"score": <float 0..1>, "passed": <bool>, "critique": "<concise assessment>"}. '
    "score is overall quality (0 = unusable, 1 = excellent). "
    "passed is true when the output is acceptable for delivery. "
    "critique is 1-4 sentences naming concrete strengths and weaknesses."
)


def judge_run(
    agent: AgentContract,
    run: dict[str, Any],
    rubric: str | None = None,
    settings: Settings | None = None,
) -> EvalOutcome:
    """Grade a run's final output with an LLM. Never raises."""
    settings = settings or get_settings()
    resolved_rubric = (rubric or "").strip() or _default_rubric(agent)
    user_prompt = _build_prompt(agent, run, resolved_rubric)

    try:
        raw = complete_simple(_SYSTEM_PROMPT, user_prompt, settings=settings)
    except Exception as exc:  # model gateway errors must not break evaluation
        return _inconclusive(resolved_rubric, f"Judge model call failed: {exc}")

    parsed = _parse(raw)
    if parsed is None:
        return _inconclusive(resolved_rubric, "Judge returned no parseable verdict.")

    score = _bounded(parsed["score"])
    critique = parsed["critique"].strip() or "No critique provided."
    passed = parsed["passed"] if parsed["passed"] is not None else score >= _PASS_THRESHOLD
    findings = [critique, f"score={score:.2f}"]
    return EvalOutcome(passed=bool(passed), score=score, rubric=resolved_rubric, findings=findings)


def _default_rubric(agent: AgentContract) -> str:
    goal = (getattr(agent, "goal", "") or "").strip()
    if goal:
        return f"The output must fully accomplish the agent's goal: {goal}"
    return DEFAULT_RUBRIC


def _build_prompt(agent: AgentContract, run: dict[str, Any], rubric: str) -> str:
    final_output = run.get("final_output")
    output_text = _stringify(final_output)
    goal = (getattr(agent, "goal", "") or "").strip() or "(not specified)"
    role = (getattr(agent, "role", "") or "").strip() or agent.agent_id
    task = _stringify(_task_from_run(run)) or "(not specified)"
    return (
        f"Agent: {agent.name} ({agent.agent_id})\n"
        f"Role: {role}\n"
        f"Goal: {goal}\n\n"
        f"Rubric:\n{rubric}\n\n"
        f"Task / input:\n{_truncate(task, 1500)}\n\n"
        f"Agent final output:\n{_truncate(output_text, 4000)}\n\n"
        "Grade the final output against the rubric and goal. Return the JSON verdict."
    )


def _task_from_run(run: dict[str, Any]) -> Any:
    payload = run.get("input_payload")
    if isinstance(payload, dict):
        messages = payload.get("messages")
        if isinstance(messages, list) and messages:
            for message in reversed(messages):
                if isinstance(message, dict) and message.get("role") == "user":
                    return message.get("content")
        return payload.get("task") or payload
    return payload


def _parse(raw: str) -> dict[str, Any] | None:
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    else:
        brace = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if brace:
            text = brace.group(0)
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(value, dict):
        return None
    score = value.get("score")
    try:
        score = float(score)
    except (TypeError, ValueError):
        return None
    passed = value.get("passed")
    if not isinstance(passed, bool):
        passed = None
    critique = value.get("critique") or value.get("reason") or value.get("feedback") or ""
    return {"score": score, "passed": passed, "critique": str(critique)}


def _inconclusive(rubric: str, reason: str) -> EvalOutcome:
    # Neutral, non-blocking: not a pass, mid score, explains why.
    return EvalOutcome(passed=False, score=0.5, rubric=rubric, findings=[reason, "score=0.50"])


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return str(value)


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n… [truncated {len(text) - limit} chars]"
