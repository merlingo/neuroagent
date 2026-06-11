import json
from pathlib import Path

from app.main import app


def test_openapi_json_matches_registered_app_paths() -> None:
    openapi = json.loads(Path("docs/openapi.json").read_text())
    documented_paths = set(openapi["paths"])
    app_paths = {route.path for route in app.routes if route.path not in {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}}
    assert app_paths <= documented_paths


def test_api_guide_mentions_core_endpoint_groups() -> None:
    guide = Path("docs/api-guide.md").read_text()
    for section in [
        "## Health",
        "## Use Cases",
        "## Domains",
        "## Agents",
        "## Runs",
        "## Approvals",
        "## Autoresearch",
        "## Documents and RAG",
        "## Tools",
        "## Obsidian",
        "## Evaluations",
    ]:
        assert section in guide


def test_api_spec_endpoint_index_includes_all_runtime_trace_routes() -> None:
    spec = Path("docs/api-spec.md").read_text()
    for route in [
        "/runs/{run_id}/steps",
        "/runs/{run_id}/tool-calls",
        "/runs/{run_id}/artifacts",
        "/approvals/pending",
        "/autoresearch/domains/{domain_id}/targets",
        "/autoresearch/domains/{domain_id}/plan",
        "/use-cases",
        "/use-cases/{use_case_id}",
        "/use-cases/{use_case_id}/run",
        "/evals/{run_id}",
    ]:
        assert route in spec
