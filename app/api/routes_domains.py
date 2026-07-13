from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.core.errors import ContractNotFoundError
from app.dependencies import get_domain_registry
from app.settings import get_settings

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
    registry = get_domain_registry()
    settings = get_settings()
    contracts_dir = Path(settings.contracts_dir)

    # Try loading from disk — either the domain already exists in registry or not
    domain_dir = contracts_dir / domain_id
    if not domain_dir.is_dir():
        # Check if already in registry (reload existing)
        try:
            domain = registry.get_domain(domain_id)
            return {"status": "reloaded", "domain_id": domain_id, "domain": domain.model_dump()}
        except ContractNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"Domain '{domain_id}' not found in registry or on disk at {domain_dir}",
            )

    # Load (or reload) from YAML on disk
    try:
        domain = registry.load_domain_from_directory(domain_dir)
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to load domain '{domain_id}' from YAML: {exc}",
        ) from exc

    agents = [a.agent_id for a in registry.list_agents() if a.domain == domain_id]
    return {
        "status": "reloaded",
        "domain_id": domain_id,
        "domain": domain.model_dump(),
        "agents_loaded": agents,
    }
