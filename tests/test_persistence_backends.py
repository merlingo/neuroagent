import httpx
import pytest

from app.db.repositories import InMemoryRepository, get_repository, repository
from app.rag.ingestion import DocumentIngestor
from app.rag.retriever import InMemoryRetriever
from app.rag.vectorstore import QdrantVectorStore, collection_name_for_model
from app.settings import Settings


def test_repository_factory_uses_memory_for_development_without_database() -> None:
    settings = Settings(app_env="development", database_url=None, repository_backend="postgres")
    assert get_repository(settings) is repository


def test_repository_factory_requires_database_url_outside_development() -> None:
    settings = Settings(app_env="production", database_url=None, repository_backend="postgres")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        get_repository(settings)


def test_in_memory_artifact_storage_inlines_small_content_and_externalizes_large_content() -> None:
    repo = InMemoryRepository(Settings(artifact_inline_max_bytes=8))
    repo.save_artifact({"run_id": "run-1", "name": "small.json", "content": "small"})
    repo.save_artifact({"run_id": "run-1", "name": "large.json", "content": "too-large"})

    small, large = repo.list_run_artifacts("run-1")
    assert small["content"] == "small"
    assert large["content"] is None
    assert large["storage_uri"].startswith("memory://artifacts/")


def test_document_ingestor_persists_metadata_chunks_and_tenant_filters() -> None:
    repo = InMemoryRepository()
    ingestor = DocumentIngestor(repo)
    result = ingestor.ingest(
        "Sigma",
        "Sigma rules represent behavioral threat vectors.",
        {},
        tenant_id="tenant-a",
        domain_id="cybersecurity",
    )

    assert repo.get_document(result["document_id"])["tenant_id"] == "tenant-a"
    assert repo.list_document_chunks(result["document_id"])
    assert InMemoryRetriever(ingestor, repo).search(
        "behavioral threat",
        tenant_id="tenant-a",
        domain_id="cybersecurity",
    )
    assert not InMemoryRetriever(ingestor, repo).search(
        "behavioral threat",
        tenant_id="tenant-b",
        domain_id="cybersecurity",
    )


def test_qdrant_collection_name_and_search_filter_payload(monkeypatch) -> None:
    settings = Settings(qdrant_url="http://qdrant:6333", qdrant_collection_prefix="na")
    assert collection_name_for_model(settings, "text-embedding-3-small", "tenant-a") == (
        "na_tenant-a_text-embedding-3-small"
    )
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return httpx.Response(200, json={"result": []}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)
    QdrantVectorStore(settings).search(
        "collection",
        [0.1],
        tenant_id="tenant-a",
        domain_id="research",
        limit=3,
        filters={"document_id": "doc-1"},
    )

    assert captured["json"]["filter"]["must"] == [
        {"key": "tenant_id", "match": {"value": "tenant-a"}},
        {"key": "domain_id", "match": {"value": "research"}},
        {"key": "document_id", "match": {"value": "doc-1"}},
    ]
