from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import APIPrincipal, api_principal, tenant_for_request, ensure_tenant_access
from app.db.repositories import get_repository
from app.dependencies import get_app_settings
from app.tools import rag_tools

router = APIRouter(tags=["documents", "rag"])


class IngestRequest(BaseModel):
    title: str
    content: str
    tenant_id: str = "default"
    domain_id: str | None = None
    source_uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    index_vectors: bool | None = None
    strict_vector: bool = False
    embedding_model: str | None = None
    collection_name: str | None = None
    collection_per_tenant: bool = False


class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    tenant_id: str = "default"
    domain_id: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    use_vector: bool | None = None
    strict_vector: bool = False
    embedding_model: str | None = None
    collection_name: str | None = None
    collection_per_tenant: bool = False


@router.post("/documents/ingest")
def ingest(request: IngestRequest, principal: APIPrincipal = Depends(api_principal)) -> dict:
    settings = get_app_settings()
    tenant_id = tenant_for_request(request.tenant_id, principal)
    index_vectors = request.index_vectors
    if index_vectors is None:
        index_vectors = settings.vector_backend == "qdrant"
    return rag_tools.ingest_document(
        {
            "title": request.title,
            "content": request.content,
            "tenant_id": tenant_id,
            "domain_id": request.domain_id,
            "source_uri": request.source_uri,
            "metadata": request.metadata,
            "index_vectors": index_vectors,
            "strict_vector": request.strict_vector,
            "embedding_model": request.embedding_model or settings.default_embedding_model,
            "collection_name": request.collection_name,
            "collection_per_tenant": request.collection_per_tenant,
        }
    )


@router.post("/documents/upload")
def upload(request: IngestRequest, principal: APIPrincipal = Depends(api_principal)) -> dict:
    return ingest(request, principal)


@router.get("/documents")
def list_documents(principal: APIPrincipal = Depends(api_principal)) -> list[dict]:
    tenant_id = tenant_for_request(None, principal)
    return get_repository().list_documents(tenant_id=tenant_id)


@router.get("/documents/{document_id}")
def get_document(document_id: str, principal: APIPrincipal = Depends(api_principal)) -> dict:
    document = get_repository().get_document(document_id)
    document = ensure_tenant_access(document, principal, "Document not found")
    document["chunks"] = get_repository().list_document_chunks(document_id)
    return document


@router.post("/rag/search")
def rag_search(request: SearchRequest, principal: APIPrincipal = Depends(api_principal)) -> dict:
    settings = get_app_settings()
    tenant_id = tenant_for_request(request.tenant_id, principal)
    use_vector = request.use_vector
    if use_vector is None:
        use_vector = settings.vector_backend == "qdrant"
    return rag_tools.search(
        {
            "query": request.query,
            "limit": request.limit,
            "tenant_id": tenant_id,
            "domain_id": request.domain_id,
            "filters": request.filters,
            "use_vector": use_vector,
            "strict_vector": request.strict_vector,
            "embedding_model": request.embedding_model or settings.default_embedding_model,
            "collection_name": request.collection_name,
            "collection_per_tenant": request.collection_per_tenant,
        }
    )
