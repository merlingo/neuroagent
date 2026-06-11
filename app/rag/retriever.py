from app.db.repositories import Repository
from app.rag.ingestion import DocumentIngestor


class InMemoryRetriever:
    def __init__(self, ingestor: DocumentIngestor, repository: Repository | None = None) -> None:
        self.ingestor = ingestor
        self.repository = repository

    def search(
        self,
        query: str,
        limit: int = 5,
        tenant_id: str | None = None,
        domain_id: str | None = None,
    ) -> list[dict]:
        terms = set(query.lower().split())
        scored = []
        chunks = []
        if self.repository is not None:
            for document in self.repository.list_documents(tenant_id=tenant_id, domain_id=domain_id):
                chunks.extend(self.repository.list_document_chunks(document["document_id"]))
        else:
            chunks = [
                {
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "metadata": chunk.metadata,
                }
                for chunk in self.ingestor.chunks
            ]
        for chunk in chunks:
            score = sum(1 for term in terms if term in chunk["text"].lower())
            if score:
                scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "chunk_id": chunk["chunk_id"],
                "source_metadata": chunk["metadata"],
                "score": float(score),
                "citation_id": f"cite:{chunk['chunk_id']}",
                "confidence": min(0.95, 0.5 + score / 10),
                "text": chunk["text"],
            }
            for score, chunk in scored[:limit]
        ]
