import pytest

from app.settings import Settings
from app.storage.artifacts import MissingArtifactStorageConfig, prepare_artifact_for_storage


class FakeObjectStorage:
    def __init__(self) -> None:
        self.puts = []

    def put_artifact(self, key: str, body: bytes, content_type: str) -> str:
        self.puts.append({"key": key, "body": body, "content_type": content_type})
        return f"s3://bucket/{key}"


def test_small_artifact_content_stays_inline_with_metadata() -> None:
    artifact = prepare_artifact_for_storage(
        {"id": "a1", "run_id": "run-1", "name": "small.json", "content": {"ok": True}},
        Settings(artifact_inline_max_bytes=1024),
        object_storage=None,
    )

    assert artifact["content"] == {"ok": True}
    assert artifact.get("storage_uri") is None
    assert artifact["metadata"]["size_bytes"] > 0
    assert artifact["metadata"]["content_hash"]


def test_large_artifact_content_is_written_to_object_storage() -> None:
    storage = FakeObjectStorage()
    artifact = prepare_artifact_for_storage(
        {
            "id": "a1",
            "run_id": "run-1",
            "artifact_type": "text",
            "name": "large.txt",
            "content": "too-large",
        },
        Settings(artifact_inline_max_bytes=4, s3_bucket="bucket"),
        object_storage=storage,
    )

    assert artifact["content"] is None
    assert artifact["storage_uri"] == "s3://bucket/artifacts/run-1/a1/large.txt"
    assert storage.puts[0]["body"] == b"too-large"
    assert storage.puts[0]["content_type"].startswith("text/plain")


def test_large_artifact_requires_object_storage_without_memory_fallback() -> None:
    with pytest.raises(MissingArtifactStorageConfig):
        prepare_artifact_for_storage(
            {"id": "a1", "run_id": "run-1", "name": "large.json", "content": "too-large"},
            Settings(artifact_inline_max_bytes=4),
            object_storage=None,
        )
