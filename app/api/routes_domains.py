from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.core.errors import ContractNotFoundError
from app.dependencies import get_domain_registry, _BUILTIN_DOMAINS
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

    # Search for the domain directory: CONTRACTS_DIR first, then built-in app/domains
    candidates = [
        Path(settings.contracts_dir) / domain_id,
        _BUILTIN_DOMAINS / domain_id,
    ]
    domain_dir = next((c for c in candidates if c.is_dir()), None)

    if domain_dir is None:
        # Not on disk — return from registry if already loaded
        try:
            domain = registry.get_domain(domain_id)
            agents = [a.agent_id for a in registry.list_agents() if a.domain == domain_id]
            return {"status": "already_loaded", "domain_id": domain_id, "domain": domain.model_dump(), "agents_loaded": agents}
        except ContractNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"Domain '{domain_id}' not found on disk (checked: {[str(c) for c in candidates]})",
            )

    # Load (or reload) from the found directory
    try:
        domain = registry.load_domain_from_directory(domain_dir)
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
