import pytest
from fastapi import HTTPException

from app.api.routes_use_cases import get_use_case, list_use_cases, run_use_case
from app.main import app


def test_use_case_routes_are_registered() -> None:
    paths = {route.path for route in app.routes}
    assert "/use-cases" in paths
    assert "/use-cases/{use_case_id}" in paths
    assert "/use-cases/{use_case_id}/run" in paths


def test_list_use_cases_exposes_expected_user_test_scenarios() -> None:
    use_case_ids = {use_case["use_case_id"] for use_case in list_use_cases()}
    assert {
        "research-agent-run",
        "cybersecurity-sigma-run",
        "rag-ingest-search",
        "autoresearch-domain-plan",
        "obsidian-note-stub",
    } <= use_case_ids


def test_get_use_case_returns_payload_and_follow_up_endpoints() -> None:
    use_case = get_use_case("research-agent-run")
    assert use_case["request_payload"]["agent_id"] == "research.literature_researcher"
    assert "GET /runs/{run_id}" in use_case["follow_up_endpoints"]


def test_get_use_case_rejects_unknown_id() -> None:
    with pytest.raises(HTTPException) as exc:
        get_use_case("missing")
    assert exc.value.status_code == 404


def test_run_research_agent_use_case_returns_traceable_run() -> None:
    result = run_use_case("research-agent-run")
    run = result["result"]
    assert run["status"] == "completed"
    assert run["agent_id"] == "research.literature_researcher"
    assert run["steps"]
    assert run["artifacts"]


def test_run_rag_use_case_returns_ingest_and_search_results() -> None:
    result = run_use_case("rag-ingest-search")
    payload = result["result"]
    assert payload["ingest"]["document_id"]
    assert payload["search_results"][0]["citation_id"].startswith("cite:")


def test_run_autoresearch_use_case_returns_program_artifacts() -> None:
    result = run_use_case("autoresearch-domain-plan")
    plan = result["result"]
    assert "program.md" in plan["artifacts"]
    assert "measurement_rubric.json" in plan["artifacts"]


def test_run_obsidian_use_case_returns_stubbed_note() -> None:
    result = run_use_case("obsidian-note-stub")
    note = result["result"]
    assert note["status"] == "stubbed"
    assert note["content"].startswith("---")
