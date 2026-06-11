from typing import Any

from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    document_id: str
    chunk_id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Evidence(BaseModel):
    chunk_id: str
    source_metadata: dict[str, Any]
    score: float
    citation_id: str
    confidence: float
    text: str
