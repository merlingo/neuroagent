import json

from fastapi import APIRouter, Depends, HTTPException

from app.auth import APIPrincipal, api_principal
from app.contracts.loop_contract import EvaluateRequest, EvaluateResponse
from app.model_gateway import ModelGatewayError, complete_simple
from app.settings import get_settings

router = APIRouter(prefix="/v1", tags=["evaluate"])

CRITIC_SYSTEM_PROMPT = """\
You are a strict iteration critic for a loop engineering system.
Your job is to evaluate whether an iteration made progress toward a goal.

You MUST respond with ONLY a JSON object matching this exact schema:
{
  "progress": "advanced" | "partial" | "none",
  "confidence": <float 0.0 to 1.0>,
  "stall_signals": [<list of short strings describing repetition or stall indicators>],
  "recommendation": "continue" | "checkpoint" | "stop",
  "reasoning": "<3 sentences max explaining your verdict>"
}

Rules:
- Compare the iteration_summary against the goal and state_document.
- Check for repetition by comparing against recent_verdicts.
- If the iteration repeats prior work or errors without new progress, set progress to "none".
- If progress is "none" for what appears to be a repeated pattern, recommend "stop".
- Be conservative: only set progress to "advanced" if clear, measurable progress was made.
- Do NOT include any text outside the JSON object.
"""


def _build_critic_user_prompt(request: EvaluateRequest) -> str:
    return json.dumps({
        "goal": request.goal,
        "state_document": request.state_document,
        "iteration_summary": request.iteration_summary,
        "recent_verdicts": request.recent_verdicts,
    }, ensure_ascii=False)


def _validate_model(model: str | None) -> str | None:
    if model is None:
        return None
    settings = get_settings()
    if not settings.neuroagent_allowed_models:
        raise HTTPException(
            status_code=422,
            detail=f"Model override '{model}' rejected: no allowed models configured",
        )
    allowed = {m.strip() for m in settings.neuroagent_allowed_models.split(",") if m.strip()}
    if model not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Model '{model}' is not in the allowed models list. Allowed: {sorted(allowed)}",
        )
    return model


def _parse_evaluate_response(text: str) -> EvaluateResponse:
    text = text.strip()
    # Try to extract JSON from potential markdown fencing
    if text.startswith("```"):
        import re
        match = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL)
        if match:
            text = match.group(1).strip()
    data = json.loads(text)
    return EvaluateResponse(**data)


@router.post("/evaluate")
def evaluate(
    request: EvaluateRequest,
    principal: APIPrincipal = Depends(api_principal),
) -> dict:
    model = _validate_model(request.model)
    settings = get_settings()
    resolved_model = model or settings.neuroagent_critic_model

    user_prompt = _build_critic_user_prompt(request)

    # Attempt up to 2 times (initial + 1 retry)
    last_error: Exception | None = None
    for _attempt in range(2):
        try:
            raw_response = complete_simple(
                system_prompt=CRITIC_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                model=resolved_model,
                settings=settings,
            )
            if not raw_response.strip():
                raise ModelGatewayError("Empty response from critic model")
            result = _parse_evaluate_response(raw_response)
            return result.model_dump()
        except (json.JSONDecodeError, TypeError, ValueError, ModelGatewayError) as exc:
            last_error = exc
            continue

    raise HTTPException(
        status_code=502,
        detail=f"Critic model returned malformed output after retry: {last_error}",
    )
