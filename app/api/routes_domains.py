from fastapi import APIRouter, HTTPException

from app.dependencies import get_domain_registry

router = APIRouter(prefix="/domains", tags=["domains"])


@router.get("")
def list_domains() -> list[dict]:
    return [domain.model_dump() for domain in get_domain_registry().list_domains()]


@router.get("/{domain_id}")
def get_domain(domain_id: str) -> dict:
    try:
        return get_domain_registry().get_domain(domain_id).model_dump()
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{domain_id}/reload")
def reload_domain(domain_id: str) -> dict:
    domain = get_domain(domain_id)
    return {"status": "reloaded", "domain": domain}
