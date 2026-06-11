from app.db.repositories import InMemoryRepository
from app.api import routes_documents
from app.settings import Settings
from app.tools import rag_tools


class RecordingVectorStore:
    def __init__(self) -> None:
        self.collection_name = ""
        self.upserts = []
        self.search_calls = []
        self.deleted = []

    def ensure_collection(self, collection_name: str, vector_size: int, distance: str = "Cosine") -> None:
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.distance = distance

    def upsert_chunks(self, collection_name, chunks, embeddings, payloads) -> None:
        self.upserts.append(
            {
                "collection_name": collection_name,
                "chunks": chunks,
                "embeddings": embeddings,
                "payloads": payloads,
            }
        )

    def search(self, collection_name, query_embedding, tenant_id, domain_id, limit, filters=None):
        self.search_calls.append(
            {
                "collection_name": collection_name,
                "query_embedding": query_embedding,
                "tenant_id": tenant_id,
                "domain_id": domain_id,
                "limit": limit,
                "filters": filters or {},
            }
        )
        return [
            {
                "id": "doc-1_chunk_0",
                "score": 0.9,
                "payload": {"document_id": "doc-1", "chunk_id": "doc-1_chunk_0"},
            }
        ]

    def delete_document_vectors(self, collection_name, document_id) -> None:
        self.deleted.append((collection_name, document_id))


def test_rag_tool_inline_search_keeps_legacy_payload_behavior() -> None:
    result = rag_tools.search(
        {
            "query": "behavioral threat",
            "documents": [{"chunk_id": "chunk-1", "text": "behavioral threat evidence"}],
        }
    )

    assert result["mode"] == "inline_lexical"
    assert result["results"][0]["citation_id"] == "cite:chunk-1"


def test_rag_tool_ingests_document_and_repository_searches_by_tenant(monkeypatch) -> None:
    repo = InMemoryRepository(Settings(vector_backend="memory"))
    monkeypatch.setattr(rag_tools, "get_repository", lambda settings=None: repo)

    ingest = rag_tools.ingest_document(
        {
            "tenant_id": "tenant-a",
            "domain_id": "research",
            "title": "RAG Note",
            "content": "alpha exclusive research evidence",
            "metadata": {"source_uri": "file://note.md"},
        }
    )
    result = rag_tools.search(
        {
            "tenant_id": "tenant-a",
            "domain_id": "research",
            "query": "alpha evidence",
            "use_vector": False,
        }
    )
    isolated = rag_tools.search(
        {
            "tenant_id": "tenant-b",
            "domain_id": "research",
            "query": "alpha evidence",
            "use_vector": False,
        }
    )

    assert ingest["status"] == "ingested"
    assert result["mode"] == "repository_lexical"
    assert result["results"]
    assert isolated["results"] == []


def test_rag_tool_indexes_document_with_vector_payloads(monkeypatch) -> None:
    repo = InMemoryRepository(Settings(vector_backend="memory"))
    store = RecordingVectorStore()
    monkeypatch.setattr(rag_tools, "get_repository", lambda settings=None: repo)
    monkeypatch.setattr(rag_tools, "get_vector_store", lambda settings=None: store)
    ingest = rag_tools.ingest_document(
        {
            "tenant_id": "tenant-a",
            "domain_id": "research",
            "title": "RAG Note",
            "content": "vector indexed evidence",
            "metadata": {"source_uri": "file://note.md"},
        }
    )

    indexed = rag_tools.index_document({"document_id": ingest["document_id"]})

    assert indexed["status"] == "indexed"
    assert store.upserts
    payload = store.upserts[0]["payloads"][0]
    assert payload["vector_id"]
    assert payload["tenant_id"] == "tenant-a"
    assert payload["domain_id"] == "research"
    assert payload["document_id"] == ingest["document_id"]
    assert repo.list_embedding_records(ingest["document_id"])
    assert repo.list_embedding_records(ingest["document_id"])[0]["vector_id"] == payload["vector_id"]


def test_rag_tool_vector_search_hydrates_repository_chunk(monkeypatch) -> None:
    repo = InMemoryRepository(Settings(vector_backend="memory"))
    store = RecordingVectorStore()
    monkeypatch.setattr(rag_tools, "get_repository", lambda settings=None: repo)
    monkeypatch.setattr(rag_tools, "get_vector_store", lambda settings=None: store)
    repo.save_document(
        {
            "id": "doc-1",
            "document_id": "doc-1",
            "tenant_id": "tenant-a",
            "domain_id": "research",
            "title": "Doc",
            "content": "vector result text",
            "metadata": {},
        }
    )
    repo.save_document_chunk(
        {
            "id": "doc-1_chunk_0",
            "chunk_id": "doc-1_chunk_0",
            "document_id": "doc-1",
            "tenant_id": "tenant-a",
            "domain_id": "research",
            "chunk_index": 0,
            "text": "vector result text",
            "metadata": {"title": "Doc"},
            "hash": "hash",
        }
    )

    result = rag_tools.search(
        {
            "tenant_id": "tenant-a",
            "domain_id": "research",
            "query": "vector",
            "use_vector": True,
        }
    )

    assert result["mode"] == "vector"
    assert result["results"][0]["text"] == "vector result text"
    assert store.search_calls[0]["tenant_id"] == "tenant-a"


def test_rag_tool_delete_vectors_uses_vector_store(monkeypatch) -> None:
    store = RecordingVectorStore()
    monkeypatch.setattr(rag_tools, "get_vector_store", lambda settings=None: store)

    result = rag_tools.delete_document_vectors({"document_id": "doc-1"})

    assert result["status"] == "deleted"
    assert store.deleted[0][1] == "doc-1"


def test_rag_api_ingest_indexes_vectors_when_qdrant_backend(monkeypatch) -> None:
    repo = InMemoryRepository(Settings(vector_backend="qdrant"))
    store = RecordingVectorStore()
    settings = Settings(vector_backend="qdrant", default_embedding_model="mock-embedding")
    monkeypatch.setattr(rag_tools, "get_repository", lambda settings=None: repo)
    monkeypatch.setattr(rag_tools, "get_vector_store", lambda settings=None: store)
    monkeypatch.setattr(routes_documents, "get_app_settings", lambda: settings)

    result = routes_documents.ingest(
        routes_documents.IngestRequest(
            tenant_id="tenant-a",
            domain_id="research",
            title="Vector Doc",
            content="qdrant indexed evidence",
            metadata={"source_uri": "file://vector.md"},
        )
    )

    assert result["status"] == "ingested"
    assert result["index"]["status"] == "indexed"
    assert store.upserts[0]["collection_name"] == "neuroagent_mock-embedding"


def test_rag_api_search_uses_vector_path_and_returns_search_envelope(monkeypatch) -> None:
    repo = InMemoryRepository(Settings(vector_backend="qdrant"))
    store = RecordingVectorStore()
    settings = Settings(vector_backend="qdrant")
    monkeypatch.setattr(rag_tools, "get_repository", lambda settings=None: repo)
    monkeypatch.setattr(rag_tools, "get_vector_store", lambda settings=None: store)
    monkeypatch.setattr(routes_documents, "get_app_settings", lambda: settings)
    repo.save_document(
        {
            "id": "doc-1",
            "document_id": "doc-1",
            "tenant_id": "tenant-a",
            "domain_id": "research",
            "title": "Doc",
            "content": "vector route text",
            "metadata": {},
        }
    )
    repo.save_document_chunk(
        {
            "id": "doc-1_chunk_0",
            "chunk_id": "doc-1_chunk_0",
            "document_id": "doc-1",
            "tenant_id": "tenant-a",
            "domain_id": "research",
            "chunk_index": 0,
            "text": "vector route text",
            "metadata": {"title": "Doc"},
            "hash": "hash",
        }
    )

    result = routes_documents.rag_search(
        routes_documents.SearchRequest(
            tenant_id="tenant-a",
            domain_id="research",
            query="vector",
        )
    )

    assert result["mode"] == "vector"
    assert result["results"][0]["text"] == "vector route text"
    assert store.search_calls[0]["collection_name"] == "neuroagent_text-embedding-3-small"
