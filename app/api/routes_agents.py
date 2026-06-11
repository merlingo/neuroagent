from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import APIPrincipal, api_principal, tenant_for_request
from app.core.runtime import AgentRuntime
from app.db.repositories import get_repository, repository as default_repository
from app.dependencies import get_domain_registry, get_tool_registry

router = APIRouter(prefix="/agents", tags=["agents"])
repository = default_repository


class RunAgentRequest(BaseModel):
    input_payload: dict[str, Any] = Field(default_factory=dict)


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
        input_payload = dict(request.input_payload)
        input_payload["tenant_id"] = tenant_for_request(input_payload.get("tenant_id"), principal)
        runtime = AgentRuntime(get_domain_registry(), get_tool_registry(), _repo())
        return runtime.run_agent(agent_id, input_payload)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _repo():
    return repository if repository is not default_repository else get_repository()
