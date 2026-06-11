import pytest
from fastapi import HTTPException

from app.api import routes_documents, routes_runs, routes_storage
from app.auth import APIPrincipal, api_principal
from app.db.repositories import repository
from app.settings import Settings


def _clear_repo() -> None:
    repository.runs.clear()
    repository.documents.clear()
    repository.approvals.clear()
    repository.audit_logs.clear()


def test_api_principal_requires_key_when_auth_enabled() -> None:
    with pytest.raises(HTTPException) as exc:
        api_principal(x_api_key=None, settings=Settings(api_auth_enabled=True))

    assert exc.value.status_code == 401
    assert exc.value.detail == "X-API-Key header is required"


def test_api_principal_resolves_tenant_and_admin_keys() -> None:
    settings = Settings(
        api_auth_enabled=True,
        api_keys="tenant-a-key:tenant-a",
        admin_api_keys="admin-key",
    )

    tenant_principal = api_principal(x_api_key="tenant-a-key", settings=settings)
    admin_principal = api_principal(x_api_key="admin-key", settings=settings)

    assert tenant_principal.tenant_id == "tenant-a"
    assert not tenant_principal.is_admin
    assert admin_principal.is_admin


def test_tenant_principal_lists_only_own_runs_and_hides_other_tenant_run() -> None:
    _clear_repo()
    routes_runs.repository = repository
    repository.save_run(
        {
            "id": "run-a",
            "tenant_id": "tenant-a",
            "domain_id": "research",
            "agent_id": "agent",
            "status": "completed",
        }
    )
    repository.save_run(
        {
            "id": "run-b",
            "tenant_id": "tenant-b",
            "domain_id": "research",
            "agent_id": "agent",
            "status": "completed",
        }
    )
    principal = APIPrincipal(tenant_id="tenant-a", api_key_id="key", authenticated=True)

    assert [run["id"] for run in routes_runs.list_runs(principal)] == ["run-a"]
    with pytest.raises(HTTPException) as exc:
        routes_runs.get_run("run-b", principal)
    assert exc.value.status_code == 404


def test_admin_principal_can_list_all_runs_and_seed_contracts() -> None:
    _clear_repo()
    routes_runs.repository = repository
    routes_storage.repository = repository
    repository.save_run(
        {
            "id": "run-a",
            "tenant_id": "tenant-a",
            "domain_id": "research",
            "agent_id": "agent",
            "status": "completed",
        }
    )
    repository.save_run(
        {
            "id": "run-b",
            "tenant_id": "tenant-b",
            "domain_id": "research",
            "agent_id": "agent",
            "status": "completed",
        }
    )
    admin = APIPrincipal(tenant_id="default", api_key_id="admin", is_admin=True, authenticated=True)
    tenant = APIPrincipal(tenant_id="tenant-a", api_key_id="key", authenticated=True)

    assert {run["id"] for run in routes_runs.list_runs(admin)} == {"run-a", "run-b"}
    with pytest.raises(HTTPException) as exc:
        routes_storage.seed_contracts(tenant)
    assert exc.value.status_code == 403
    assert routes_storage.seed_contracts(admin)["backend"] == "InMemoryRepository"


def test_tenant_principal_cannot_ingest_or_search_as_another_tenant() -> None:
    _clear_repo()
    principal = APIPrincipal(tenant_id="tenant-a", api_key_id="key", authenticated=True)

    with pytest.raises(HTTPException) as ingest_exc:
        routes_documents.ingest(
            routes_documents.IngestRequest(
                tenant_id="tenant-b",
                title="Doc",
                content="secret",
            ),
            principal,
        )
    assert ingest_exc.value.status_code == 403

    with pytest.raises(HTTPException) as search_exc:
        routes_documents.rag_search(
            routes_documents.SearchRequest(tenant_id="tenant-b", query="secret"),
            principal,
        )
    assert search_exc.value.status_code == 403
