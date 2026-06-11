from fastapi import APIRouter, Depends, HTTPException

from app.auth import APIPrincipal, api_principal, current_principal, ensure_tenant_access
from app.db.repositories import get_repository, repository as default_repository

repository = default_repository

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("")
def list_runs(principal: APIPrincipal = Depends(api_principal)) -> list[dict]:
    resolved = current_principal(principal)
    runs = _repo().list_runs()
    if resolved.is_admin:
        return runs
    return [run for run in runs if run.get("tenant_id") == resolved.tenant_id]


@router.get("/{run_id}")
def get_run(run_id: str, principal: APIPrincipal = Depends(api_principal)) -> dict:
    run = _repo().get_run(run_id)
    return ensure_tenant_access(run, principal, "Run not found")


@router.get("/{run_id}/steps")
def get_steps(run_id: str, principal: APIPrincipal = Depends(api_principal)) -> list[dict]:
    get_run(run_id, principal)
    return _repo().list_run_steps(run_id)


@router.get("/{run_id}/tool-calls")
def get_tool_calls(run_id: str, principal: APIPrincipal = Depends(api_principal)) -> list[dict]:
    get_run(run_id, principal)
    return _repo().list_run_tool_calls(run_id)


@router.get("/{run_id}/artifacts")
def get_artifacts(run_id: str, principal: APIPrincipal = Depends(api_principal)) -> list[dict]:
    get_run(run_id, principal)
    return _repo().list_run_artifacts(run_id)


@router.post("/{run_id}/cancel")
def cancel_run(run_id: str, principal: APIPrincipal = Depends(api_principal)) -> dict:
    get_run(run_id, principal)
    cancelled = _repo().update_run(run_id, {"status": "cancelled"})
    if cancelled is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return cancelled


def _repo():
    return repository if repository is not default_repository else get_repository()
