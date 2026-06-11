import base64
from typing import Any

import httpx
import pytest

from app.core.errors import ApprovalRequiredError
from app.domains.registry import DomainRegistry
from app.settings import get_settings
from app.tools import github_tools
from app.tools.policy import ToolPolicy
from app.tools.registry import ToolRegistry


@pytest.fixture(autouse=True)
def github_env(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_DEFAULT_OWNER", "neurobytes")
    monkeypatch.setenv("GITHUB_DEFAULT_REPO", "neuroagent")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _response(method: str, url: str, payload: dict | list) -> httpx.Response:
    return httpx.Response(200, json=payload, request=httpx.Request(method, url))


def test_github_tool_requires_token(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    get_settings.cache_clear()

    with pytest.raises(github_tools.GitHubToolError, match="GITHUB_TOKEN"):
        github_tools.get_repo({"owner": "octo", "repo": "hello"})


def test_get_repo_uses_auth_headers_and_defaults(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_request(method, url, headers, params, json, timeout):
        captured.update(method=method, url=url, headers=headers, params=params, json=json, timeout=timeout)
        return _response(
            method,
            url,
            {
                "name": "neuroagent",
                "full_name": "neurobytes/neuroagent",
                "owner": {"login": "neurobytes"},
                "private": False,
                "default_branch": "main",
                "html_url": "https://github.com/neurobytes/neuroagent",
            },
        )

    monkeypatch.setattr(httpx, "request", fake_request)
    result = github_tools.get_repo({})

    assert captured["url"].endswith("/repos/neurobytes/neuroagent")
    assert captured["headers"]["Authorization"] == "Bearer test-token"
    assert captured["headers"]["X-GitHub-Api-Version"] == "2022-11-28"
    assert result["full_name"] == "neurobytes/neuroagent"


def test_list_issues_forwards_filters(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_request(method, url, headers, params, json, timeout):
        captured.update(method=method, url=url, params=params)
        return _response(
            method,
            url,
            [
                {
                    "number": 1,
                    "title": "Bug",
                    "state": "open",
                    "html_url": "https://github.com/neurobytes/neuroagent/issues/1",
                    "user": {"login": "mert"},
                    "labels": [{"name": "bug"}],
                    "body": "body",
                }
            ],
        )

    monkeypatch.setattr(httpx, "request", fake_request)
    result = github_tools.list_issues({"state": "all", "labels": "bug", "per_page": 10})

    assert captured["params"]["state"] == "all"
    assert captured["params"]["labels"] == "bug"
    assert result["issues"][0]["labels"] == ["bug"]


def test_get_file_decodes_base64_content(monkeypatch) -> None:
    content = base64.b64encode(b"hello").decode("ascii")

    def fake_request(method, url, headers, params, json, timeout):
        return _response(
            method,
            url,
            {
                "path": "README.md",
                "sha": "abc",
                "encoding": "base64",
                "content": content,
                "html_url": "https://github.com/neurobytes/neuroagent/blob/main/README.md",
            },
        )

    monkeypatch.setattr(httpx, "request", fake_request)
    result = github_tools.get_file({"path": "README.md", "ref": "main"})

    assert result["content"] == "hello"
    assert result["sha"] == "abc"


def test_create_issue_and_comment_send_expected_payloads(monkeypatch) -> None:
    calls = []

    def fake_request(method, url, headers, params, json, timeout):
        calls.append((method, url, json))
        if url.endswith("/comments"):
            return _response(
                method,
                url,
                {"id": 11, "body": json["body"], "html_url": "https://github.com/comment", "user": {"login": "mert"}},
            )
        return _response(
            method,
            url,
            {
                "number": 2,
                "title": json["title"],
                "state": "open",
                "html_url": "https://github.com/issue",
                "user": {"login": "mert"},
                "labels": [{"name": "task"}],
                "body": json["body"],
            },
        )

    monkeypatch.setattr(httpx, "request", fake_request)
    issue = github_tools.create_issue({"title": "Task", "body": "Do it", "labels": ["task"]})
    comment = github_tools.create_issue_comment({"issue_number": 2, "body": "Comment"})

    assert issue["issue"]["number"] == 2
    assert comment["comment"]["body"] == "Comment"
    assert calls[0][2]["labels"] == ["task"]
    assert calls[1][2] == {"body": "Comment"}


def test_update_file_encodes_content(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_request(method, url, headers, params, json, timeout):
        captured.update(method=method, url=url, json=json)
        return _response(
            method,
            url,
            {
                "content": {"path": "README.md", "sha": "new-sha", "html_url": "https://github.com/file"},
                "commit": {"sha": "commit-sha"},
            },
        )

    monkeypatch.setattr(httpx, "request", fake_request)
    result = github_tools.update_file(
        {"path": "README.md", "content": "hello", "message": "Update README", "sha": "old-sha"}
    )

    assert captured["method"] == "PUT"
    assert captured["json"]["content"] == base64.b64encode(b"hello").decode("ascii")
    assert captured["json"]["sha"] == "old-sha"
    assert result["commit_sha"] == "commit-sha"


def test_github_write_tools_require_approval_by_policy() -> None:
    agent = DomainRegistry.from_default_path().get_agent("research.literature_researcher").model_copy(
        update={"allowed_tools": ["github.create_issue", "github.create_issue_comment", "github.update_file"]}
    )
    registry = ToolRegistry.from_default_path()

    for tool_id in ["github.create_issue", "github.create_issue_comment", "github.update_file"]:
        with pytest.raises(ApprovalRequiredError):
            ToolPolicy().validate(agent, registry.get(tool_id))
