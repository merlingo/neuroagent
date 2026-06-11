from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi import HTTPException

from app.auth import APIPrincipal, current_principal, require_admin
from app.db.repositories import get_repository
from app.dependencies import get_app_settings, get_domain_registry, get_tool_registry

router = APIRouter(tags=["storage", "admin"])


@router.get("/storage/status")
def storage_status() -> dict:
    settings = get_app_settings()
    repo = get_repository(settings)
    db_status = "memory"
    if settings.repository_backend == "postgres":
        db_status = "configured" if settings.database_url else "missing_database_url"
    artifact_backend = "s3" if settings.s3_bucket else "inline"
    artifact_status = "configured"
    if artifact_backend == "s3" and (not settings.s3_access_key or not settings.s3_secret_key):
        artifact_status = "missing_credentials"
    return {
        "database": {
            "backend": settings.repository_backend,
            "status": db_status,
        },
        "vector": {
            "backend": settings.vector_backend,
            "status": "configured" if settings.vector_backend == "qdrant" and settings.qdrant_url else "memory",
            "url": settings.qdrant_url if settings.vector_backend == "qdrant" else None,
        },
        "artifacts": {
            "backend": artifact_backend,
            "status": artifact_status,
            "endpoint": settings.s3_endpoint or None,
            "bucket": settings.s3_bucket or None,
            "inline_max_bytes": settings.artifact_inline_max_bytes,
        },
        "repository_class": repo.__class__.__name__,
    }


@router.post("/admin/db/seed-contracts")
def seed_contracts(principal: APIPrincipal = Depends(require_admin)) -> dict:
    if not current_principal(principal).is_admin:
        raise HTTPException(status_code=403, detail="Admin API key required")
    repo = get_repository()
    domains = get_domain_registry().list_domains()
    agents = get_domain_registry().list_agents()
    tools = get_tool_registry().list()
    prompts = list(Path("app/prompts/templates").glob("*.md"))

    if repo.__class__.__name__ != "SQLAlchemyRepository":
        repo.append_audit_log(
            {
                "action": "seed_contracts",
                "resource_type": "contracts",
                "payload": {"backend": repo.__class__.__name__, "persisted": False},
            }
        )
        return {
            "persisted": False,
            "backend": repo.__class__.__name__,
            "domains": len(domains),
            "agents": len(agents),
            "tools": len(tools),
            "prompts": len(prompts),
        }

    from app.db.models import AgentDefinition, DomainStack, PromptTemplate, ToolDefinition, ToolPolicy

    with repo.session_factory() as session:
        for domain in domains:
            payload = domain.model_dump()
            session.merge(
                DomainStack(
                    id=domain.domain_id,
                    domain_id=domain.domain_id,
                    name=domain.name,
                    version=domain.version,
                    status=domain.status,
                    contract=payload,
                )
            )
            session.merge(
                ToolPolicy(
                    id=f"{domain.domain_id}.risk_policy",
                    policy_id=f"{domain.domain_id}.risk_policy",
                    domain_id=domain.domain_id,
                    rules=domain.risk_policy.model_dump(),
                )
            )
        for agent in agents:
            payload = agent.model_dump()
            session.merge(
                AgentDefinition(
                    id=agent.agent_id,
                    agent_id=agent.agent_id,
                    domain_id=agent.domain,
                    name=agent.name,
                    version=agent.version,
                    risk_level=agent.risk_level,
                    contract=payload,
                )
            )
        for tool in tools:
            payload = tool.model_dump()
            session.merge(
                ToolDefinition(
                    id=tool.tool_id,
                    tool_id=tool.tool_id,
                    name=tool.name,
                    version=tool.version,
                    risk_level=tool.risk_level,
                    requires_approval=tool.requires_approval,
                    contract=payload,
                )
            )
        for prompt_path in prompts:
            session.merge(
                PromptTemplate(
                    id=f"prompt.{prompt_path.stem}",
                    template_id=prompt_path.stem,
                    name=prompt_path.stem,
                    version="1.0.0",
                    content=prompt_path.read_text(),
                    metadata_={"source_path": str(prompt_path)},
                )
            )
        session.commit()

    repo.append_audit_log(
        {
            "id": str(uuid4()),
            "action": "seed_contracts",
            "resource_type": "contracts",
            "payload": {"persisted": True},
        }
    )
    return {
        "persisted": True,
        "backend": repo.__class__.__name__,
        "domains": len(domains),
        "agents": len(agents),
        "tools": len(tools),
        "prompts": len(prompts),
    }
