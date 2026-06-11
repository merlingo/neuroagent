from uuid import uuid4
import hashlib

from app.db.repositories import Repository
from app.rag.chunking import TextChunker
from app.rag.schemas import DocumentChunk


class DocumentIngestor:
    def __init__(self, repository: Repository | None = None) -> None:
        self.repository = repository
        self.documents: dict[str, dict] = {}
        self.chunks: list[DocumentChunk] = []
        self.chunker = TextChunker()

    def ingest(
        self,
        title: str,
        content: str,
        metadata: dict,
        tenant_id: str = "default",
        domain_id: str | None = None,
        source_uri: str | None = None,
    ) -> dict:
        document_id = str(uuid4())
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        document = {
            "id": document_id,
            "document_id": document_id,
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "source_type": metadata.get("source_type", "text"),
            "source_uri": source_uri or metadata.get("source_uri"),
            "title": title,
            "content": content,
            "hash": content_hash,
            "metadata": metadata,
        }
        self.documents[document_id] = document
        chunks = self.chunker.chunk(
            document_id,
            content,
            {"title": title, "source_uri": document["source_uri"], **metadata},
        )
        self.chunks.extend(chunks)
        if self.repository is not None:
            self.repository.save_document(document)
            for index, chunk in enumerate(chunks):
                self.repository.save_document_chunk(
                    {
                        "id": chunk.chunk_id,
                        "chunk_id": chunk.chunk_id,
                        "document_id": document_id,
                        "tenant_id": tenant_id,
                        "domain_id": domain_id,
                        "chunk_index": index,
                        "text": chunk.text,
                        "metadata": chunk.metadata,
                        "hash": hashlib.sha256(chunk.text.encode("utf-8")).hexdigest(),
                    }
                )
        return {"document_id": document_id, "chunk_count": len(chunks)}
