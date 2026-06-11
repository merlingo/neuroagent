from typing import Any, Literal

from pydantic import BaseModel, Field


class ArtifactContract(BaseModel):
    artifact_type: Literal["markdown", "json", "text", "yaml"]
    name: str
    content: str | dict[str, Any]
    storage_uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
