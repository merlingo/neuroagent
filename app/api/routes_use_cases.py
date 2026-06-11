from fastapi import APIRouter, HTTPException

from app.db.repositories import get_repository, repository as default_repository
from app.dependencies import get_domain_registry, get_tool_registry
from app.rag.ingestion import DocumentIngestor
from app.use_cases import UseCaseRunner

router = APIRouter(prefix="/use-cases", tags=["use-cases"])
repository = default_repository


def get_runner() -> UseCaseRunner:
    active_repository = repository if repository is not default_repository else get_repository()
    return UseCaseRunner(
        repository=active_repository,
        domain_registry=get_domain_registry(),
        tool_registry=get_tool_registry(),
        ingestor=DocumentIngestor(active_repository),
    )


@router.get("")
def list_use_cases() -> list[dict]:
    return [use_case.model_dump() for use_case in get_runner().list_use_cases()]


@router.get("/{use_case_id}")
def get_use_case(use_case_id: str) -> dict:
    use_case = get_runner().get_use_case(use_case_id)
    if use_case is None:
        raise HTTPException(status_code=404, detail="Use case not found")
    return use_case.model_dump()


@router.post("/{use_case_id}/run")
def run_use_case(use_case_id: str) -> dict:
    result = get_runner().run(use_case_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Use case not found")
    return result
