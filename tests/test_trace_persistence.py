from pathlib import Path

from app.api.routes_runs import cancel_run, get_artifacts, get_steps, get_tool_calls
from app.core.runtime import AgentRuntime
from app.db.repositories import InMemoryRepository
from app.domains.registry import DomainRegistry
from app.tools.registry import ToolRegistry


def build_runtime(repo: InMemoryRepository) -> AgentRuntime:
    return AgentRuntime(
        DomainRegistry.from_default_path(),
        ToolRegistry.from_default_path(),
        repo,
    )


def test_runtime_persists_steps_as_first_class_trace_records() -> None:
    repo = InMemoryRepository()
    run = build_runtime(repo).run_agent(
        "cybersecurity.sigma_rule_agent",
        {"threat_description": "encoded PowerShell", "target_platform": "windows"},
    )

    assert run["steps"] == repo.list_run_steps(run["id"])
    assert len(repo.steps) == len(run["resolved_plan"]["steps"])
    assert all(step["run_id"] == run["id"] for step in repo.steps)


def test_runtime_persists_artifacts_and_evaluations_separately() -> None:
    repo = InMemoryRepository()
    run = build_runtime(repo).run_agent(
        "research.literature_researcher",
        {"research_question": "agent governance"},
    )

    assert repo.list_run_artifacts(run["id"])[0]["name"] == "run_trace.json"
    assert repo.list_run_evaluations(run["id"])
    assert all(result["run_id"] == run["id"] for result in repo.list_run_evaluations(run["id"]))


def test_runtime_persists_tool_calls_with_step_reference() -> None:
    repo = InMemoryRepository()
    run = build_runtime(repo).run_agent(
        "research.literature_researcher",
        {"research_question": "agent governance"},
    )

    tool_calls = repo.list_run_tool_calls(run["id"])
    assert tool_calls
    assert tool_calls[0]["step_id"] == "write_obsidian_note"
    assert tool_calls[0]["id"]


def test_repository_get_run_rehydrates_trace_collections() -> None:
    repo = InMemoryRepository()
    run = build_runtime(repo).run_agent(
        "cybersecurity.sigma_rule_agent",
        {"threat_description": "encoded PowerShell", "target_platform": "windows"},
    )

    raw_run = repo.runs[run["id"]]
    assert "steps" not in raw_run
    hydrated = repo.get_run(run["id"])
    assert hydrated is not None
    assert hydrated["steps"]
    assert hydrated["tool_calls"]
    assert hydrated["artifacts"]
    assert hydrated["evaluations"]


def test_run_routes_read_trace_collections_from_repository(monkeypatch) -> None:
    from app.api import routes_runs

    repo = InMemoryRepository()
    run = build_runtime(repo).run_agent(
        "research.literature_researcher",
        {"research_question": "agent governance"},
    )
    monkeypatch.setattr(routes_runs, "repository", repo)

    assert get_steps(run["id"]) == repo.list_run_steps(run["id"])
    assert get_tool_calls(run["id"]) == repo.list_run_tool_calls(run["id"])
    assert get_artifacts(run["id"]) == repo.list_run_artifacts(run["id"])


def test_cancel_run_updates_status_without_losing_trace(monkeypatch) -> None:
    from app.api import routes_runs

    repo = InMemoryRepository()
    run = build_runtime(repo).run_agent(
        "research.literature_researcher",
        {"research_question": "agent governance"},
    )
    monkeypatch.setattr(routes_runs, "repository", repo)

    cancelled = cancel_run(run["id"])
    assert cancelled["status"] == "cancelled"
    assert cancelled["steps"]
    assert cancelled["artifacts"]


def test_initial_migration_defines_trace_tables() -> None:
    migration = Path("app/db/migrations/versions/0001_initial_trace_tables.py").read_text()
    for table_name in [
        "agent_runs",
        "agent_steps",
        "tool_calls",
        "artifacts",
        "evaluation_results",
        "approval_requests",
    ]:
        assert f'"{table_name}"' in migration


def test_alembic_env_targets_project_metadata() -> None:
    env = Path("app/db/migrations/env.py").read_text()
    assert "target_metadata = Base.metadata" in env
    assert "settings.database_url" in env
