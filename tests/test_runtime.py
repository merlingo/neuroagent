from app.core.runtime import AgentRuntime
from app.db.repositories import InMemoryRepository
from app.domains.registry import DomainRegistry
from app.tools.registry import ToolRegistry


def test_agent_run_lifecycle() -> None:
    runtime = AgentRuntime(
        DomainRegistry.from_default_path(),
        ToolRegistry.from_default_path(),
        InMemoryRepository(),
    )
    run = runtime.run_agent(
        "cybersecurity.sigma_rule_agent",
        {"threat_description": "encoded PowerShell", "target_platform": "windows"},
    )
    assert run["status"] == "completed"
    assert run["steps"]
    assert run["artifacts"][0]["name"] == "run_trace.json"
    assert run["evaluations"]
