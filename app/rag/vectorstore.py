from __future__ import annotations

from typing import Any, Protocol

import httpx

from app.settings import Settings, get_settings


class VectorStore(Protocol):
    def ensure_collection(self, collection_name: str, vector_size: int, distance: str = "Cosine") -> None: ...
    def upsert_chunks(
        self,
        collection_name: str,
        chunks: list[dict],
        embeddings: list[list[float]],
        payloads: list[dict],
    ) -> None: ...
    def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        tenant_id: str,
        domain_id: str | None,
        limit: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict]: ...
    def delete_document_vectors(self, collection_name: str, document_id: str) -> None: ...


def collection_name_for_model(settings: Settings, embedding_model: str, tenant_id: str | None = None) -> str:
    normalized = embedding_model.replace("/", "-").replace(":", "-").replace(".", "-")
    if tenant_id:
        return f"{settings.qdrant_collection_prefix}_{tenant_id}_{normalized}"
    return f"{settings.qdrant_collection_prefix}_{normalized}"


class InMemoryVectorStore:
    def __init__(self) -> None:
        self.collections: dict[str, dict] = {}
        self.records: list[dict] = []

    def ensure_collection(self, collection_name: str, vector_size: int, distance: str = "Cosine") -> None:
        self.collections[collection_name] = {"vector_size": vector_size, "distance": distance}

    def upsert(self, record: dict) -> None:
        self.records.append(record)

    def upsert_chunks(
        self,
        collection_name: str,
        chunks: list[dict],
        embeddings: list[list[float]],
        payloads: list[dict],
    ) -> None:
        for chunk, embedding, payload in zip(chunks, embeddings, payloads, strict=True):
            self.records.append(
                {
                    "collection_name": collection_name,
                    "id": chunk["chunk_id"],
                    "vector": embedding,
                    "payload": payload,
                }
            )

    def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        tenant_id: str,
        domain_id: str | None,
        limit: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict]:
        matches = []
        for record in self.records:
            payload = record.get("payload", {})
            if record.get("collection_name") != collection_name:
                continue
            if payload.get("tenant_id") != tenant_id:
                continue
            if domain_id is not None and payload.get("domain_id") != domain_id:
                continue
            if filters and any(payload.get(key) != value for key, value in filters.items()):
                continue
            score = 1.0
            matches.append({"id": record["id"], "score": score, "payload": payload})
        return matches[:limit]

    def delete_document_vectors(self, collection_name: str, document_id: str) -> None:
        self.records = [
            record
            for record in self.records
            if record.get("collection_name") != collection_name
            or record.get("payload", {}).get("document_id") != document_id
        ]


class QdrantVectorStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.base_url = self.settings.qdrant_url.rstrip("/")
        self.headers = {}
        if self.settings.qdrant_api_key:
            self.headers["api-key"] = self.settings.qdrant_api_key

    def ensure_collection(self, collection_name: str, vector_size: int, distance: str = "Cosine") -> None:
        payload = {"vectors": {"size": vector_size, "distance": distance}}
        response = httpx.put(
            f"{self.base_url}/collections/{collection_name}",
            headers=self.headers,
            json=payload,
            timeout=10,
        )
        response.raise_for_status()

    def upsert_chunks(
        self,
        collection_name: str,
        chunks: list[dict],
        embeddings: list[list[float]],
        payloads: list[dict],
    ) -> None:
        points = [
            {
                "id": payload.get("vector_id", chunk["chunk_id"]),
                "vector": embedding,
                "payload": payload,
            }
            for chunk, embedding, payload in zip(chunks, embeddings, payloads, strict=True)
        ]
        response = httpx.put(
            f"{self.base_url}/collections/{collection_name}/points",
            headers=self.headers,
            json={"points": points},
            timeout=30,
        )
        response.raise_for_status()

    def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        tenant_id: str,
        domain_id: str | None,
        limit: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict]:
        must = [{"key": "tenant_id", "match": {"value": tenant_id}}]
        if domain_id is not None:
            must.append({"key": "domain_id", "match": {"value": domain_id}})
        for key, value in (filters or {}).items():
            must.append({"key": key, "match": {"value": value}})
        response = httpx.post(
            f"{self.base_url}/collections/{collection_name}/points/search",
            headers=self.headers,
            json={"vector": query_embedding, "limit": limit, "with_payload": True, "filter": {"must": must}},
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("result", [])

    def delete_document_vectors(self, collection_name: str, document_id: str) -> None:
        response = httpx.post(
            f"{self.base_url}/collections/{collection_name}/points/delete",
            headers=self.headers,
            json={
                "filter": {
                    "must": [{"key": "document_id", "match": {"value": document_id}}],
                }
            },
            timeout=10,
        )
        response.raise_for_status()


def get_vector_store(settings: Settings | None = None) -> VectorStore:
    settings = settings or get_settings()
    if settings.vector_backend == "qdrant":
        return QdrantVectorStore(settings)
    return InMemoryVectorStore()
