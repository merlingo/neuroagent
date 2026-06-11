from __future__ import annotations

import base64
from typing import Any

import httpx

from app.settings import get_settings


class GitHubToolError(RuntimeError):
    pass


def _require_token() -> str:
    token = get_settings().github_token
    if not token:
        raise GitHubToolError("GITHUB_TOKEN is required for GitHub tools")
    return token


def _repo(payload: dict[str, Any]) -> tuple[str, str]:
    settings = get_settings()
    owner = payload.get("owner") or settings.github_default_owner
    repo = payload.get("repo") or settings.github_default_repo
    if not owner or not repo:
        raise GitHubToolError("owner and repo are required, or configure GITHUB_DEFAULT_OWNER/GITHUB_DEFAULT_REPO")
    return str(owner), str(repo)


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_require_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_payload: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any]:
    settings = get_settings()
    url = f"{settings.github_api_base_url.rstrip('/')}{path}"
    try:
        response = httpx.request(
            method,
            url,
            headers=_headers(),
            params={key: value for key, value in (params or {}).items() if value is not None},
            json=json_payload,
            timeout=settings.github_timeout_seconds,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise GitHubToolError(
            f"GitHub API request failed with status {exc.response.status_code}: {method} {path}"
        ) from exc
    except httpx.HTTPError as exc:
        raise GitHubToolError(f"GitHub API request failed: {method} {path}") from exc
    if response.status_code == 204 or not response.content:
        return {}
    data = response.json()
    if not isinstance(data, (dict, list)):
        raise GitHubToolError("GitHub API returned an unsupported response shape")
    return data


def _content_item(data: dict[str, Any] | list[Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise GitHubToolError("GitHub content response must be an object")
    return data


def _decode_content(data: dict[str, Any]) -> str:
    content = data.get("content", "")
    encoding = data.get("encoding")
    if encoding != "base64":
        raise GitHubToolError(f"Unsupported GitHub content encoding: {encoding}")
    compact = str(content).replace("\n", "")
    return base64.b64decode(compact).decode("utf-8")


def get_repo(payload: dict[str, Any]) -> dict:
    owner, repo = _repo(payload)
    data = _request("GET", f"/repos/{owner}/{repo}")
    if not isinstance(data, dict):
        raise GitHubToolError("GitHub repo response must be an object")
    return {
        "status": "fetched",
        "owner": data.get("owner", {}).get("login", owner),
        "repo": data.get("name", repo),
        "full_name": data.get("full_name", f"{owner}/{repo}"),
        "private": data.get("private"),
        "default_branch": data.get("default_branch"),
        "html_url": data.get("html_url"),
        "description": data.get("description"),
    }


def get_issue(payload: dict[str, Any]) -> dict:
    owner, repo = _repo(payload)
    issue_number = payload.get("issue_number") or payload.get("number")
    if not issue_number:
        raise GitHubToolError("issue_number is required")
    data = _request("GET", f"/repos/{owner}/{repo}/issues/{issue_number}")
    if not isinstance(data, dict):
        raise GitHubToolError("GitHub issue response must be an object")
    return _issue_summary(data)


def lookup_issue(payload: dict[str, Any]) -> dict:
    return get_issue(payload)


def list_issues(payload: dict[str, Any]) -> dict:
    owner, repo = _repo(payload)
    params = {
        "state": payload.get("state", "open"),
        "labels": payload.get("labels"),
        "since": payload.get("since"),
        "per_page": payload.get("per_page", 30),
    }
    data = _request("GET", f"/repos/{owner}/{repo}/issues", params=params)
    if not isinstance(data, list):
        raise GitHubToolError("GitHub issues response must be a list")
    return {
        "status": "fetched",
        "owner": owner,
        "repo": repo,
        "issues": [_issue_summary(item) for item in data if isinstance(item, dict)],
    }


def create_issue(payload: dict[str, Any]) -> dict:
    owner, repo = _repo(payload)
    title = payload.get("title")
    if not title:
        raise GitHubToolError("title is required")
    body = payload.get("body", "")
    data = _request(
        "POST",
        f"/repos/{owner}/{repo}/issues",
        json_payload={"title": title, "body": body, "labels": payload.get("labels", [])},
    )
    if not isinstance(data, dict):
        raise GitHubToolError("GitHub create issue response must be an object")
    return {"status": "created", "issue": _issue_summary(data)}


def create_issue_comment(payload: dict[str, Any]) -> dict:
    owner, repo = _repo(payload)
    issue_number = payload.get("issue_number") or payload.get("number")
    body = payload.get("body")
    if not issue_number:
        raise GitHubToolError("issue_number is required")
    if not body:
        raise GitHubToolError("body is required")
    data = _request(
        "POST",
        f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
        json_payload={"body": body},
    )
    if not isinstance(data, dict):
        raise GitHubToolError("GitHub comment response must be an object")
    return {
        "status": "created",
        "comment": {
            "id": data.get("id"),
            "body": data.get("body"),
            "html_url": data.get("html_url"),
            "user": (data.get("user") or {}).get("login"),
        },
    }


def get_file(payload: dict[str, Any]) -> dict:
    owner, repo = _repo(payload)
    path = payload.get("path")
    if not path:
        raise GitHubToolError("path is required")
    params = {"ref": payload.get("ref")}
    data = _content_item(_request("GET", f"/repos/{owner}/{repo}/contents/{path}", params=params))
    return {
        "status": "fetched",
        "owner": owner,
        "repo": repo,
        "path": data.get("path", path),
        "sha": data.get("sha"),
        "encoding": data.get("encoding"),
        "content": _decode_content(data),
        "html_url": data.get("html_url"),
    }


def update_file(payload: dict[str, Any]) -> dict:
    owner, repo = _repo(payload)
    path = payload.get("path")
    content = payload.get("content")
    message = payload.get("message")
    sha = payload.get("sha")
    if not path:
        raise GitHubToolError("path is required")
    if content is None:
        raise GitHubToolError("content is required")
    if not message:
        raise GitHubToolError("message is required")
    if not sha:
        raise GitHubToolError("sha is required")
    encoded = base64.b64encode(str(content).encode("utf-8")).decode("ascii")
    body = {
        "message": message,
        "content": encoded,
        "sha": sha,
        "branch": payload.get("branch"),
    }
    data = _request("PUT", f"/repos/{owner}/{repo}/contents/{path}", json_payload=body)
    if not isinstance(data, dict):
        raise GitHubToolError("GitHub update file response must be an object")
    content_response = data.get("content") or {}
    commit_response = data.get("commit") or {}
    return {
        "status": "updated",
        "path": content_response.get("path", path),
        "sha": content_response.get("sha"),
        "html_url": content_response.get("html_url"),
        "commit_sha": commit_response.get("sha"),
    }


def _issue_summary(data: dict[str, Any]) -> dict:
    return {
        "number": data.get("number"),
        "title": data.get("title"),
        "state": data.get("state"),
        "html_url": data.get("html_url"),
        "user": (data.get("user") or {}).get("login"),
        "labels": [label.get("name") for label in data.get("labels", []) if isinstance(label, dict)],
        "body": data.get("body"),
    }
