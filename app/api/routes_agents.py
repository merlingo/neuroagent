from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import APIPrincipal, api_principal, tenant_for_request
from app.contracts.loop_contract import LoopContext
from app.core.idempotency import idempotency_cache
from app.core.runtime import AgentRuntime
from app.db.repositories import get_repository, repository as default_repository
from app.dependencies import get_domain_registry, get_tool_registry
from app.settings import get_settings

router = APIRouter(prefix="/agents", tags=["agents"])
repository = default_repository


class RunAgentRequest(BaseModel):
    input_payload: dict[str, Any] = Field(default_factory=dict)
    model: str | None = None
    loop_context: LoopContext | None = None
    max_steps: int | None = None
    max_tokens: int | None = None
    client_run_id: str | None = None


def _validate_model_override(model: str | None) -> None:
    if model is None:
        return
    settings = get_settings()
    if not settings.neuroagent_allowed_models:
        raise HTTPException(
            status_code=422,
            detail=f"Model override '{model}' rejected: no allowed models configured (NEUROAGENT_ALLOWED_MODELS is empty)",
        )
    allowed = {m.strip() for m in settings.neuroagent_allowed_models.split(",") if m.strip()}
    if model not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Model '{model}' is not in the allowed models list. Allowed: {sorted(allowed)}",
        )


@router.get("")
def list_agents() -> list[dict]:
    return [agent.model_dump() for agent in get_domain_registry().list_agents()]


@router.get("/{agent_id}")
def get_agent(agent_id: str) -> dict:
    try:
        return get_domain_registry().get_agent(agent_id).model_dump()
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{agent_id}/run")
def run_agent(
    agent_id: str,
    request: RunAgentRequest,
    principal: APIPrincipal = Depends(api_principal),
) -> dict:
    try:
        # Validate model override
        _validate_model_override(request.model)

        input_payload = dict(request.input_payload)
        tenant_id = tenant_for_request(input_payload.get("tenant_id"), principal)
        input_payload["tenant_id"] = tenant_id

        # Idempotency check
        if request.client_run_id:
            existing_run_id = idempotency_cache.check_and_set(
                tenant_id, request.client_run_id, "pending"
            )
            if existing_run_id is not None:
                raise HTTPException(
                    status_code=409,
                    detail=f"Duplicate client_run_id: already processed as run '{existing_run_id}'",
                )

        settings = get_settings()
        runtime = AgentRuntime(get_domain_registry(), get_tool_registry(), _repo())
        result = runtime.run_agent(
            agent_id,
            input_payload,
            model_override=request.model,
            loop_context=request.loop_context,
            max_steps=request.max_steps or settings.neuroagent_default_max_steps,
            max_tokens=request.max_tokens or settings.neuroagent_default_max_tokens,
        )

        # Update idempotency cache with real run_id
        if request.client_run_id and result.get("id"):
            idempotency_cache.update(tenant_id, request.client_run_id, result["id"])

        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _repo():
    return repository if repository is not default_repository else get_repository()
