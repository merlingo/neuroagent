import pytest
from pathlib import Path

import httpx

from app.core.errors import ContractNotFoundError
from app.settings import get_settings
from app.tools.registry import ToolRegistry


SAMPLE_PAYLOADS = {
    "local.echo": {"value": 42},
    "file.write_artifact": {"name": "report.md", "content": "hello"},
    "file.read_file": {"path": "pyproject.toml"},
    "file.write_file": {"path": ".pytest-tool-registry/write.txt", "content": "hello"},
    "file.update_file": {
        "path": ".pytest-tool-registry/update.txt",
        "content": "updated content",
    },
    "file.delete_file": {"path": ".pytest-tool-registry/delete.txt", "missing_ok": True},
    "obsidian.write_note": {"title": "Registry Test", "body": "hello"},
    "rag.search": {
        "query": "behavioral threat",
        "documents": [{"chunk_id": "chunk-1", "text": "behavioral threat evidence"}],
    },
    "rag.ingest_document": {
        "tenant_id": "default",
        "domain_id": "research",
        "title": "Registry RAG",
        "content": "behavioral threat evidence",
    },
    "rag.delete_document_vectors": {"document_id": "missing-doc"},
    "web.search": {"query": "agent governance", "limit": 1},
    "citation.verify": {"citations": [{"url": "https://example.com/source"}]},
    "sigma.validate_yaml": {
        "content": "title: Test\nlogsource:\n  product: windows\ndetection:\n  selection: {}\n  condition: selection\n"
    },
    "yara.validate_rule": {"content": "rule TestRule { condition: true }"},
    "mitre.lookup": {"technique": "T1059"},
    "github.get_repo": {"owner": "neurobytes", "repo": "neuroagent"},
    "github.get_issue": {"owner": "neurobytes", "repo": "neuroagent", "issue_number": 1},
    "github.list_issues": {"owner": "neurobytes", "repo": "neuroagent"},
    "github.create_issue": {"owner": "neurobytes", "repo": "neuroagent", "title": "Task", "body": "Body"},
    "github.create_issue_comment": {
        "owner": "neurobytes",
        "repo": "neuroagent",
        "issue_number": 1,
        "body": "Comment",
    },
    "github.get_file": {"owner": "neurobytes", "repo": "neuroagent", "path": "README.md"},
    "github.update_file": {
        "owner": "neurobytes",
        "repo": "neuroagent",
        "path": "README.md",
        "content": "hello",
        "message": "Update",
        "sha": "old-sha",
    },
    "shell.execute": {"command": "date"},
}


@pytest.fixture(autouse=True)
def clean_registry_files():
    root = Path(".pytest-tool-registry")
    root.mkdir(exist_ok=True)
    (root / "update.txt").write_text("initial content")
    yield
    for path in sorted(root.glob("**/*"), reverse=True):
        if path.is_file():
            path.unlink()
    if root.exists():
        for path in sorted(root.glob("**/*"), reverse=True):
            if path.is_dir():
                path.rmdir()
        root.rmdir()


@pytest.fixture(autouse=True)
def github_registry_env(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    get_settings.cache_clear()

    def fake_request(method, url, headers, params, json, timeout):
        if url.endswith("/issues") and method == "GET":
            payload = [
                {
                    "number": 1,
                    "title": "Issue",
                    "state": "open",
                    "html_url": "https://github.com/issue",
                    "user": {"login": "mert"},
                    "labels": [],
                    "body": "body",
                }
            ]
        elif url.endswith("/issues") and method == "POST":
            payload = {
                "number": 2,
                "title": json["title"],
                "state": "open",
                "html_url": "https://github.com/issue",
                "user": {"login": "mert"},
                "labels": [],
                "body": json["body"],
            }
        elif url.endswith("/comments"):
            payload = {
                "id": 3,
                "body": json["body"],
                "html_url": "https://github.com/comment",
                "user": {"login": "mert"},
            }
        elif "/contents/" in url and method == "GET":
            payload = {
                "path": "README.md",
                "sha": "sha",
                "encoding": "base64",
                "content": "aGVsbG8=",
                "html_url": "https://github.com/file",
            }
        elif "/contents/" in url and method == "PUT":
            payload = {
                "content": {"path": "README.md", "sha": "new-sha", "html_url": "https://github.com/file"},
                "commit": {"sha": "commit-sha"},
            }
        elif "/issues/" in url:
            payload = {
                "number": 1,
                "title": "Issue",
                "state": "open",
                "html_url": "https://github.com/issue",
                "user": {"login": "mert"},
                "labels": [],
                "body": "body",
            }
        else:
            payload = {
                "name": "neuroagent",
                "full_name": "neurobytes/neuroagent",
                "owner": {"login": "neurobytes"},
                "private": False,
                "default_branch": "main",
                "html_url": "https://github.com/neurobytes/neuroagent",
            }
        return httpx.Response(200, json=payload, request=httpx.Request(method, url))

    monkeypatch.setattr(httpx, "request", fake_request)
    yield
    get_settings.cache_clear()


def test_all_registered_tools_have_handlers() -> None:
    registry = ToolRegistry.from_default_path()
    assert registry.missing_handlers() == []


@pytest.mark.parametrize("tool_id", sorted(SAMPLE_PAYLOADS))
def test_all_tools_run_through_registry(tool_id: str) -> None:
    registry = ToolRegistry.from_default_path()
    result = registry.run(tool_id, SAMPLE_PAYLOADS[tool_id])

    assert isinstance(result, dict)
    assert result


def test_registry_run_rejects_unknown_tool_instead_of_echo_fallback() -> None:
    registry = ToolRegistry.from_default_path()
    with pytest.raises(ContractNotFoundError):
        registry.run("missing.tool", {"value": 1})


def test_shell_execute_registry_handler_does_not_execute_command() -> None:
    registry = ToolRegistry.from_default_path()
    result = registry.run("shell.execute", {"command": "date"})

    assert result["status"] == "approval_required"
    assert result["command"] == "date"
