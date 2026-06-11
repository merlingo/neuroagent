from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.autoresearcher.pipeline import AutoresearchDomainImprovementPipeline
from app.autoresearcher.schemas import DomainImprovementTarget
from app.dependencies import get_domain_registry

router = APIRouter(prefix="/autoresearch", tags=["autoresearch"])


class AutoresearchPlanRequest(BaseModel):
    budget_minutes: int = Field(default=30, ge=1, le=1440)
    primary_metric: str = "eval_pass_rate"
    targets: list[DomainImprovementTarget] = Field(default_factory=list)


@router.get("/domains/{domain_id}/targets")
def default_targets(domain_id: str) -> list[dict]:
    try:
        get_domain_registry().get_domain(domain_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [
        target.model_dump()
        for target in AutoresearchDomainImprovementPipeline().default_targets(domain_id)
    ]


@router.post("/domains/{domain_id}/plan")
def create_plan(domain_id: str, request: AutoresearchPlanRequest) -> dict:
    try:
        get_domain_registry().get_domain(domain_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    plan = AutoresearchDomainImprovementPipeline().plan(
        domain_id=domain_id,
        targets=request.targets,
        budget_minutes=request.budget_minutes,
        primary_metric=request.primary_metric,
    )
    return plan.model_dump()


@router.post("/domains/{domain_id}/improvement-run")
def create_improvement_run(domain_id: str, request: AutoresearchPlanRequest) -> dict:
    try:
        get_domain_registry().get_domain(domain_id)
        run = AutoresearchDomainImprovementPipeline().run_improvement(
            domain_id=domain_id,
            targets=request.targets,
            budget_minutes=request.budget_minutes,
            primary_metric=request.primary_metric,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return run.model_dump()
