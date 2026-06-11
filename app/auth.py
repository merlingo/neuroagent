from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from fastapi.params import Depends as DependsParam

from app.settings import Settings, get_settings


@dataclass(frozen=True)
class APIPrincipal:
    tenant_id: str
    api_key_id: str = "anonymous"
    is_admin: bool = False
    authenticated: bool = False


def api_principal(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> APIPrincipal:
    if not settings.api_auth_enabled:
        return APIPrincipal(
            tenant_id=settings.default_tenant_id,
            api_key_id="auth-disabled",
            is_admin=True,
            authenticated=False,
        )
    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header is required")

    admin_keys = _token_set(settings.admin_api_keys)
    if x_api_key in admin_keys:
        return APIPrincipal(
            tenant_id=settings.default_tenant_id,
            api_key_id=_fingerprint(x_api_key),
            is_admin=True,
            authenticated=True,
        )

    tenant_id = _tenant_for_key(settings.api_keys, x_api_key)
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return APIPrincipal(
        tenant_id=tenant_id,
        api_key_id=_fingerprint(x_api_key),
        is_admin=False,
        authenticated=True,
    )


def require_admin(principal: APIPrincipal = Depends(api_principal)) -> APIPrincipal:
    if not principal.is_admin:
        raise HTTPException(status_code=403, detail="Admin API key required")
    return principal


def current_principal(value: object) -> APIPrincipal:
    if isinstance(value, APIPrincipal):
        return value
    settings = get_settings()
    return APIPrincipal(
        tenant_id=settings.default_tenant_id,
        api_key_id="direct-call",
        is_admin=True,
        authenticated=False,
    )


def tenant_for_request(requested_tenant_id: str | None, principal: object) -> str:
    resolved = current_principal(principal)
    tenant_id = requested_tenant_id or resolved.tenant_id
    if resolved.is_admin:
        return tenant_id
    if tenant_id != resolved.tenant_id:
        raise HTTPException(status_code=403, detail="API key is not authorized for this tenant")
    return tenant_id


def ensure_tenant_access(record: dict | None, principal: object, not_found_detail: str) -> dict:
    if not record:
        raise HTTPException(status_code=404, detail=not_found_detail)
    resolved = current_principal(principal)
    if resolved.is_admin or record.get("tenant_id") == resolved.tenant_id:
        return record
    raise HTTPException(status_code=404, detail=not_found_detail)


def is_dependency_placeholder(value: object) -> bool:
    return isinstance(value, DependsParam)


def _tenant_for_key(config: str, api_key: str) -> str | None:
    for entry in _entries(config):
        if ":" in entry:
            key, tenant_id = entry.split(":", 1)
        else:
            key, tenant_id = entry, get_settings().default_tenant_id
        if api_key == key.strip():
            return tenant_id.strip() or get_settings().default_tenant_id
    return None


def _token_set(config: str) -> set[str]:
    return {entry.strip() for entry in _entries(config)}


def _entries(config: str) -> list[str]:
    return [entry.strip() for entry in config.split(",") if entry.strip()]


def _fingerprint(api_key: str) -> str:
    if len(api_key) <= 8:
        return api_key
    return f"{api_key[:4]}...{api_key[-4:]}"
