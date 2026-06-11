from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol

from app.settings import Settings


class ArtifactObjectStorage(Protocol):
    def put_artifact(self, key: str, body: bytes, content_type: str) -> str: ...


class MissingArtifactStorageConfig(RuntimeError):
    pass


class S3ArtifactStorage:
    def __init__(self, settings: Settings) -> None:
        if not settings.s3_bucket:
            raise MissingArtifactStorageConfig("S3_BUCKET is required for large artifact storage")
        if not settings.s3_access_key or not settings.s3_secret_key:
            raise MissingArtifactStorageConfig("S3_ACCESS_KEY and S3_SECRET_KEY are required")
        try:
            import boto3
        except ImportError as exc:
            raise MissingArtifactStorageConfig("boto3 is required for S3 artifact storage") from exc

        self.settings = settings
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint or None,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )

    def put_artifact(self, key: str, body: bytes, content_type: str) -> str:
        self.client.put_object(
            Bucket=self.settings.s3_bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )
        return f"s3://{self.settings.s3_bucket}/{key}"


def prepare_artifact_for_storage(
    artifact: dict[str, Any],
    settings: Settings,
    object_storage: ArtifactObjectStorage | None,
    memory_fallback: bool = False,
) -> dict[str, Any]:
    artifact = dict(artifact)
    metadata = dict(artifact.get("metadata", {}))
    content = artifact.get("content")
    if content is None:
        artifact["metadata"] = metadata
        return artifact

    body, content_type = serialize_artifact_content(content, artifact.get("artifact_type", "json"))
    metadata.setdefault("content_hash", hashlib.sha256(body).hexdigest())
    metadata.setdefault("size_bytes", len(body))

    if len(body) <= settings.artifact_inline_max_bytes:
        artifact["metadata"] = metadata
        return artifact

    artifact_id = artifact.get("id", metadata.get("id", "artifact"))
    run_id = artifact.get("run_id", "run")
    name = _safe_key_part(artifact.get("name", artifact_id))
    key = artifact.get("storage_key") or f"artifacts/{run_id}/{artifact_id}/{name}"

    if object_storage is not None:
        artifact["storage_uri"] = object_storage.put_artifact(key, body, content_type)
    elif memory_fallback:
        artifact["storage_uri"] = artifact.get("storage_uri") or f"memory://artifacts/{artifact_id}"
    else:
        raise MissingArtifactStorageConfig("Large artifact requires configured object storage")

    artifact["content"] = None
    artifact["metadata"] = metadata
    return artifact


def serialize_artifact_content(content: Any, artifact_type: str = "json") -> tuple[bytes, str]:
    if isinstance(content, bytes):
        return content, "application/octet-stream"
    if isinstance(content, str):
        return content.encode("utf-8"), _content_type_for(artifact_type)
    return json.dumps(content, default=str, ensure_ascii=False, sort_keys=True).encode("utf-8"), "application/json"


def _content_type_for(artifact_type: str) -> str:
    return {
        "markdown": "text/markdown; charset=utf-8",
        "text": "text/plain; charset=utf-8",
        "yaml": "application/yaml; charset=utf-8",
        "json": "application/json",
    }.get(artifact_type, "application/octet-stream")


def _safe_key_part(value: str) -> str:
    safe = value.replace("\\", "-").replace("/", "-").strip()
    return safe or "artifact"
