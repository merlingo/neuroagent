from __future__ import annotations

from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from app.db.repositories import Repository, get_repository
from app.rag.embeddings import MockEmbeddingProvider
from app.rag.ingestion import DocumentIngestor
from app.rag.vectorstore import collection_name_for_model, get_vector_store
from app.settings import Settings, get_settings


class RAGToolError(RuntimeError):
    pass


def ingest_document(payload: dict) -> dict:
    title = payload.get("title")
    content = payload.get("content")
    if not title:
        raise RAGToolError("title is required")
    if not content:
        raise RAGToolError("content is required")

    settings = get_settings()
    repository = get_repository(settings)
    tenant_id = payload.get("tenant_id") or settings.default_tenant_id
    domain_id = payload.get("domain_id")
    metadata = payload.get("metadata", {})
    source_uri = payload.get("source_uri") or metadata.get("source_uri")

    result = DocumentIngestor(repository).ingest(
        title=title,
        content=content,
        metadata=metadata,
        tenant_id=tenant_id,
        domain_id=domain_id,
        source_uri=source_uri,
    )
    if payload.get("index_vectors", False):
        index_payload = {
            "document_id": result["document_id"],
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "source_uri": source_uri,
            "embedding_model": payload.get("embedding_model"),
            "collection_name": payload.get("collection_name"),
            "collection_per_tenant": payload.get("collection_per_tenant", False),
        }
        try:
            result["index"] = index_document(index_payload)
        except Exception as exc:
            if payload.get("strict_vector", False):
                raise
            result["index"] = {
                "status": "index_skipped",
                "reason": str(exc),
                "vector_backend": settings.vector_backend,
            }
    return {"status": "ingested", **result}


def index_document(payload: dict) -> dict:
    settings = get_settings()
    repository = get_repository(settings)
    document_id = payload.get("document_id")
    if not document_id:
        raise RAGToolError("document_id is required")
    document = repository.get_document(document_id)
    if document is None:
        raise RAGToolError(f"document not found: {document_id}")
    chunks = repository.list_document_chunks(document_id)
    if not chunks:
        raise RAGToolError(f"document has no chunks: {document_id}")

    embedding_model = payload.get("embedding_model") or settings.default_embedding_model
    tenant_id = payload.get("tenant_id") or document.get("tenant_id") or settings.default_tenant_id
    domain_id = payload.get("domain_id", document.get("domain_id"))
    collection_name = payload.get("collection_name") or collection_name_for_model(
        settings,
        embedding_model,
        tenant_id if payload.get("collection_per_tenant", False) else None,
    )
    provider = MockEmbeddingProvider()
    embeddings = [provider.embed(chunk["text"]) for chunk in chunks]
    vector_store = get_vector_store(settings)
    vector_store.ensure_collection(collection_name, vector_size=len(embeddings[0]))
    vector_payloads = [
        _vector_payload(
            chunk=chunk,
            document=document,
            tenant_id=tenant_id,
            domain_id=domain_id,
            embedding_model=embedding_model,
        )
        for chunk in chunks
    ]
    vector_store.upsert_chunks(collection_name, chunks, embeddings, vector_payloads)

    for chunk, payload_item in zip(chunks, vector_payloads, strict=True):
        repository.save_embedding_record(
            {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "document_id": document_id,
                "chunk_id": chunk["chunk_id"],
                "embedding_model": embedding_model,
                "vector_backend": settings.vector_backend,
                "collection_name": collection_name,
                "vector_id": payload_item["vector_id"],
            }
        )
    return {
        "status": "indexed",
        "document_id": document_id,
        "chunk_count": len(chunks),
        "embedding_model": embedding_model,
        "vector_backend": settings.vector_backend,
        "collection_name": collection_name,
    }


def search(payload: dict) -> dict:
    query = payload.get("query", "")
    if not query:
        raise RAGToolError("query is required")
    limit = int(payload.get("limit", 5))
    tenant_id = payload.get("tenant_id") or get_settings().default_tenant_id
    domain_id = payload.get("domain_id")
    filters = payload.get("filters", {})

    if payload.get("documents") is not None:
        results = _lexical_search(
            query=query,
            chunks=_inline_chunks(payload["documents"]),
            limit=limit,
            filters=filters,
        )
        return _search_response(query, results, "inline_lexical")

    settings = get_settings()
    repository = get_repository(settings)
    if payload.get("use_vector", True):
        vector_results = _vector_search(payload, repository, settings, query, tenant_id, domain_id, limit, filters)
        if vector_results:
            return _search_response(query, vector_results, "vector")

    chunks = _repository_chunks(repository, tenant_id=tenant_id, domain_id=domain_id)
    results = _lexical_search(query=query, chunks=chunks, limit=limit, filters=filters)
    return _search_response(query, results, "repository_lexical")


def delete_document_vectors(payload: dict) -> dict:
    document_id = payload.get("document_id")
    if not document_id:
        raise RAGToolError("document_id is required")
    settings = get_settings()
    embedding_model = payload.get("embedding_model") or settings.default_embedding_model
    tenant_id = payload.get("tenant_id")
    collection_name = payload.get("collection_name") or collection_name_for_model(
        settings,
        embedding_model,
        tenant_id if payload.get("collection_per_tenant", False) else None,
    )
    try:
        get_vector_store(settings).delete_document_vectors(collection_name, document_id)
    except Exception:
        if payload.get("strict_vector", False):
            raise
        return {
            "status": "delete_skipped",
            "document_id": document_id,
            "collection_name": collection_name,
        }
    return {
        "status": "deleted",
        "document_id": document_id,
        "collection_name": collection_name,
    }


def _vector_search(
    payload: dict,
    repository: Repository,
    settings: Settings,
    query: str,
    tenant_id: str,
    domain_id: str | None,
    limit: int,
    filters: dict[str, Any],
) -> list[dict]:
    embedding_model = payload.get("embedding_model") or settings.default_embedding_model
    collection_name = payload.get("collection_name") or collection_name_for_model(
        settings,
        embedding_model,
        tenant_id if payload.get("collection_per_tenant", False) else None,
    )
    query_embedding = MockEmbeddingProvider().embed(query)
    try:
        matches = get_vector_store(settings).search(
            collection_name=collection_name,
            query_embedding=query_embedding,
            tenant_id=tenant_id,
            domain_id=domain_id,
            limit=limit,
            filters=filters,
        )
    except Exception:
        if payload.get("strict_vector", False):
            raise
        return []
    return _hydrate_vector_matches(repository, matches, limit)


def _hydrate_vector_matches(repository: Repository, matches: list[dict], limit: int) -> list[dict]:
    results = []
    for match in matches:
        payload = match.get("payload", {})
        document_id = payload.get("document_id")
        chunk_id = payload.get("chunk_id") or match.get("id")
        chunk = _find_chunk(repository, document_id, chunk_id)
        text = chunk.get("text") if chunk else payload.get("text", "")
        metadata = chunk.get("metadata", payload) if chunk else payload
        results.append(
            {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "score": float(match.get("score", 0.0)),
                "citation_id": f"cite:{chunk_id}",
                "confidence": min(0.95, 0.55 + float(match.get("score", 0.0)) / 10),
                "source_metadata": metadata,
                "text": text,
            }
        )
    return results[:limit]


def _find_chunk(repository: Repository, document_id: str | None, chunk_id: str | None) -> dict | None:
    if not document_id or not chunk_id:
        return None
    for chunk in repository.list_document_chunks(document_id):
        if chunk["chunk_id"] == chunk_id:
            return chunk
    return None


def _repository_chunks(repository: Repository, tenant_id: str, domain_id: str | None) -> list[dict]:
    chunks = []
    for document in repository.list_documents(tenant_id=tenant_id, domain_id=domain_id):
        chunks.extend(repository.list_document_chunks(document["document_id"]))
    return chunks


def _inline_chunks(documents: list[dict]) -> list[dict]:
    chunks = []
    for index, document in enumerate(documents):
        chunks.append(
            {
                "chunk_id": document.get("chunk_id", f"inline_chunk_{index}"),
                "document_id": document.get("document_id", f"inline_doc_{index}"),
                "text": str(document.get("text", document.get("content", ""))),
                "metadata": document.get("metadata", {}),
            }
        )
    return chunks


def _lexical_search(query: str, chunks: list[dict], limit: int, filters: dict[str, Any]) -> list[dict]:
    terms = set(query.lower().split())
    scored = []
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        if filters and any(_filter_value(chunk, metadata, key) != value for key, value in filters.items()):
            continue
        text = chunk.get("text", "")
        score = sum(1 for term in terms if term in text.lower())
        if score:
            scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [_result_from_chunk(chunk, float(score)) for score, chunk in scored[:limit]]


def _filter_value(chunk: dict, metadata: dict, key: str) -> Any:
    return chunk.get(key, metadata.get(key))


def _result_from_chunk(chunk: dict, score: float) -> dict:
    chunk_id = chunk["chunk_id"]
    return {
        "chunk_id": chunk_id,
        "document_id": chunk.get("document_id"),
        "score": score,
        "citation_id": f"cite:{chunk_id}",
        "confidence": min(0.95, 0.5 + score / 10),
        "source_metadata": chunk.get("metadata", {}),
        "text": chunk.get("text", ""),
    }


def _search_response(query: str, results: list[dict], mode: str) -> dict:
    return {
        "status": "searched",
        "mode": mode,
        "query": query,
        "results": results,
    }


def _vector_payload(
    chunk: dict,
    document: dict,
    tenant_id: str,
    domain_id: str | None,
    embedding_model: str,
) -> dict:
    vector_id = str(uuid5(NAMESPACE_URL, f"neuroagent:{embedding_model}:{chunk['chunk_id']}"))
    return {
        "vector_id": vector_id,
        "tenant_id": tenant_id,
        "domain_id": domain_id,
        "document_id": document["document_id"],
        "chunk_id": chunk["chunk_id"],
        "source_uri": document.get("source_uri"),
        "title": document.get("title"),
        "hash": chunk.get("hash", document.get("hash")),
        "embedding_model": embedding_model,
    }
