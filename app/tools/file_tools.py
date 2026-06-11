from __future__ import annotations

from pathlib import Path
from typing import Any

from app.settings import get_settings


class FileToolError(RuntimeError):
    pass


def _root() -> Path:
    settings = get_settings()
    root = Path(settings.file_tool_root or settings.project_root or ".")
    return root.resolve()


def _resolve_path(path_value: str) -> Path:
    if not path_value:
        raise FileToolError("path is required")
    root = _root()
    path = Path(path_value)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (root / path).resolve()
    if resolved != root and root not in resolved.parents:
        raise FileToolError(f"path must stay within FILE_TOOL_ROOT: {path_value}")
    return resolved


def _payload_path(payload: dict[str, Any]) -> Path:
    return _resolve_path(str(payload.get("path") or payload.get("file_path") or ""))


def read_file(payload: dict[str, Any]) -> dict:
    path = _payload_path(payload)
    encoding = payload.get("encoding", "utf-8")
    if not path.exists():
        raise FileToolError(f"file not found: {path}")
    if not path.is_file():
        raise FileToolError(f"path is not a file: {path}")
    content = path.read_text(encoding=encoding)
    return {
        "status": "read",
        "path": str(path),
        "content": content,
        "size_bytes": path.stat().st_size,
    }


def write_file(payload: dict[str, Any]) -> dict:
    path = _payload_path(payload)
    content = str(payload.get("content", payload.get("body", "")))
    encoding = payload.get("encoding", "utf-8")
    overwrite = bool(payload.get("overwrite", True))
    if path.exists() and not overwrite:
        raise FileToolError(f"file already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=encoding)
    return {
        "status": "written",
        "path": str(path),
        "size_bytes": path.stat().st_size,
    }


def update_file(payload: dict[str, Any]) -> dict:
    path = _payload_path(payload)
    encoding = payload.get("encoding", "utf-8")
    if not path.exists():
        raise FileToolError(f"file not found: {path}")
    content = path.read_text(encoding=encoding)
    if "content" in payload or "body" in payload:
        new_content = str(payload.get("content", payload.get("body", "")))
    else:
        old = payload.get("old")
        new = payload.get("new")
        if old is None or new is None:
            raise FileToolError("update_file requires content/body or old/new replacement fields")
        occurrences = content.count(str(old))
        if occurrences == 0:
            raise FileToolError("old text was not found")
        replace_all = bool(payload.get("replace_all", False))
        count = -1 if replace_all else 1
        new_content = content.replace(str(old), str(new), count)
    path.write_text(new_content, encoding=encoding)
    return {
        "status": "updated",
        "path": str(path),
        "size_bytes": path.stat().st_size,
    }


def delete_file(payload: dict[str, Any]) -> dict:
    path = _payload_path(payload)
    missing_ok = bool(payload.get("missing_ok", False))
    if not path.exists():
        if missing_ok:
            return {"status": "missing", "path": str(path)}
        raise FileToolError(f"file not found: {path}")
    if not path.is_file():
        raise FileToolError(f"path is not a file: {path}")
    path.unlink()
    return {"status": "deleted", "path": str(path)}


def write_artifact(payload: dict[str, Any]) -> dict:
    name = payload.get("name") or payload.get("artifact_name") or "artifact.txt"
    content = payload.get("content", payload.get("body", ""))
    return {
        "status": "written",
        "artifact_name": name,
        "content": content,
        "metadata": payload.get("metadata", {}),
    }
