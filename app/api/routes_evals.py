from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import APIPrincipal, api_principal, current_principal, ensure_tenant_access
from app.db.repositories import get_repository, repository as default_repository
from app.dependencies import get_domain_registry
from app.evals.llm_judge import JUDGE_EVAL_NAME, judge_run
from app.evals.reports import build_report

router = APIRouter(prefix="/evals", tags=["evals"])
repository = default_repository


class JudgeRequest(BaseModel):
    rubric: str | None = None


@router.post("/run/{run_id}")
def run_evals(run_id: str, principal: APIPrincipal = Depends(api_principal)) -> list[dict]:
    run = _repo().get_run(run_id)
    ensure_tenant_access(run, principal, "Run not found")
    return _repo().list_run_evaluations(run_id)


@router.post("/judge/{run_id}")
def judge(
    run_id: str,
    body: JudgeRequest | None = None,
    principal: APIPrincipal = Depends(api_principal),
) -> dict:
    """Run the LLM-as-judge over a completed run's final output and persist it."""
    run = _repo().get_run(run_id)
    ensure_tenant_access(run, principal, "Run not found")
    try:
        agent = get_domain_registry().get_agent(run["agent_id"])
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Agent for run not found: {exc}") from exc

    outcome = judge_run(agent, run, rubric=(body.rubric if body else None))
    evaluation = {
        "run_id": run_id,
        "eval_name": JUDGE_EVAL_NAME,
        "passed": outcome.passed,
        "score": outcome.score,
        "rubric": outcome.rubric,
        "findings": outcome.findings,
    }
    _repo().save_evaluation(evaluation)
    return evaluation


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
