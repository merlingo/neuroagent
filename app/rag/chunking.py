from app.rag.schemas import DocumentChunk


class TextChunker:
    def chunk(self, document_id: str, text: str, metadata: dict, size: int = 800) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        for index, start in enumerate(range(0, len(text), size)):
            chunks.append(
                DocumentChunk(
                    document_id=document_id,
                    chunk_id=f"{document_id}_chunk_{index}",
                    text=text[start : start + size],
                    metadata=metadata,
                )
            )
        return chunks
