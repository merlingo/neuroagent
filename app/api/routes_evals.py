from fastapi import APIRouter, Depends, HTTPException

from app.auth import APIPrincipal, api_principal, current_principal, ensure_tenant_access
from app.db.repositories import get_repository, repository as default_repository
from app.evals.reports import build_report

router = APIRouter(prefix="/evals", tags=["evals"])
repository = default_repository


@router.post("/run/{run_id}")
def run_evals(run_id: str, principal: APIPrincipal = Depends(api_principal)) -> list[dict]:
    run = _repo().get_run(run_id)
    ensure_tenant_access(run, principal, "Run not found")
    return _repo().list_run_evaluations(run_id)


@router.get("/reports")
def reports(principal: APIPrincipal = Depends(api_principal)) -> list[dict]:
    resolved = current_principal(principal)
    runs = _repo().list_runs()
    if not resolved.is_admin:
        runs = [run for run in runs if run.get("tenant_id") == resolved.tenant_id]
    return [build_report(runs)]


@router.get("/{run_id}")
def get_evals(run_id: str, principal: APIPrincipal = Depends(api_principal)) -> list[dict]:
    return run_evals(run_id, principal)


def _repo():
    return repository if repository is not default_repository else get_repository()
