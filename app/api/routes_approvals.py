from fastapi import APIRouter, Depends, HTTPException

from app.auth import APIPrincipal, api_principal, current_principal, ensure_tenant_access
from app.db.repositories import get_repository, repository as default_repository

router = APIRouter(prefix="/approvals", tags=["approvals"])
repository = default_repository


@router.get("/pending")
def pending_approvals(principal: APIPrincipal = Depends(api_principal)) -> list[dict]:
    resolved = current_principal(principal)
    approvals = _repo().list_pending_approvals()
    if resolved.is_admin:
        return approvals
    return [approval for approval in approvals if approval.get("tenant_id") == resolved.tenant_id]


@router.post("/{approval_id}/approve")
def approve(approval_id: str, principal: APIPrincipal = Depends(api_principal)) -> dict:
    ensure_tenant_access(_repo().get_approval(approval_id), principal, "Approval request not found")
    approval = _repo().update_approval(approval_id, "approved")
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return approval


@router.post("/{approval_id}/reject")
def reject(approval_id: str, principal: APIPrincipal = Depends(api_principal)) -> dict:
    ensure_tenant_access(_repo().get_approval(approval_id), principal, "Approval request not found")
    approval = _repo().update_approval(approval_id, "rejected")
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return approval


def _repo():
    return repository if repository is not default_repository else get_repository()
