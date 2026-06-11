from pathlib import Path

import pytest

from app.settings import get_settings
from app.tools import file_tools


@pytest.fixture(autouse=True)
def clear_settings_cache_after_test():
    yield
    get_settings.cache_clear()


def _set_file_root(monkeypatch, root: Path) -> None:
    monkeypatch.setenv("FILE_TOOL_ROOT", str(root))
    get_settings.cache_clear()


def test_file_tools_read_write_update_delete_within_root(tmp_path: Path, monkeypatch) -> None:
    _set_file_root(monkeypatch, tmp_path)

    written = file_tools.write_file({"path": "notes/example.txt", "content": "hello world"})
    assert written["status"] == "written"

    read = file_tools.read_file({"path": "notes/example.txt"})
    assert read["content"] == "hello world"

    updated = file_tools.update_file({"path": "notes/example.txt", "old": "world", "new": "agent"})
    assert updated["status"] == "updated"
    assert file_tools.read_file({"path": "notes/example.txt"})["content"] == "hello agent"

    deleted = file_tools.delete_file({"path": "notes/example.txt"})
    assert deleted["status"] == "deleted"
    assert not (tmp_path / "notes/example.txt").exists()


def test_file_tools_reject_paths_outside_root(tmp_path: Path, monkeypatch) -> None:
    _set_file_root(monkeypatch, tmp_path)

    with pytest.raises(file_tools.FileToolError, match="FILE_TOOL_ROOT"):
        file_tools.read_file({"path": "../outside.txt"})


def test_write_file_respects_overwrite_false(tmp_path: Path, monkeypatch) -> None:
    _set_file_root(monkeypatch, tmp_path)
    file_tools.write_file({"path": "file.txt", "content": "first"})

    with pytest.raises(file_tools.FileToolError, match="already exists"):
        file_tools.write_file({"path": "file.txt", "content": "second", "overwrite": False})


def test_update_file_requires_replacement_or_content(tmp_path: Path, monkeypatch) -> None:
    _set_file_root(monkeypatch, tmp_path)
    file_tools.write_file({"path": "file.txt", "content": "first"})

    with pytest.raises(file_tools.FileToolError, match="requires"):
        file_tools.update_file({"path": "file.txt"})
