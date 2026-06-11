from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api.routes_agents import RunAgentRequest, get_agent, list_agents, run_agent
from app.api.routes_domains import get_domain, list_domains
from app.api.routes_evals import reports
from app.api.routes_tools import ToolTestRequest, get_tool, list_tools, test_tool as run_tool_test
from app.contracts.agent_contract import AgentContract
from app.core.artifacts import ArtifactWriter
from app.core.errors import ContractNotFoundError, ToolPolicyError
from app.core.intent_router import IntentRouter
from app.core.planner import SimplePlanner
from app.db.repositories import InMemoryRepository
from app.domains.registry import DomainRegistry
from app.evals.reports import summarize
from app.obsidian.note_writer import ObsidianNoteWriter
from app.prompts.renderer import render
from app.prompts.validators import has_required_variables
from app.rag.chunking import TextChunker
from app.rag.embeddings import MockEmbeddingProvider
from app.rag.ingestion import DocumentIngestor
from app.rag.reranker import IdentityReranker
from app.rag.retriever import InMemoryRetriever
from app.tools.executor import ToolExecutor
from app.tools.policy import ToolPolicy
from app.tools.registry import ToolRegistry


def test_domain_route_lists_seeded_domains() -> None:
    domain_ids = {domain["domain_id"] for domain in list_domains()}
    assert {"research", "cybersecurity", "productivity", "investor_gtm"} <= domain_ids


def test_domain_route_returns_404_for_unknown_domain() -> None:
    with pytest.raises(HTTPException) as exc:
        get_domain("missing")
    assert exc.value.status_code == 404


def test_agent_route_lists_seeded_agents() -> None:
    agent_ids = {agent["agent_id"] for agent in list_agents()}
    assert "research.literature_researcher" in agent_ids
    assert "cybersecurity.sigma_rule_agent" in agent_ids


def test_agent_route_returns_404_for_unknown_agent() -> None:
    with pytest.raises(HTTPException) as exc:
        get_agent("missing.agent")
    assert exc.value.status_code == 404


def test_tool_route_lists_registered_tools() -> None:
    tool_ids = {tool["tool_id"] for tool in list_tools()}
    assert {"obsidian.write_note", "rag.search", "shell.execute"} <= tool_ids


def test_tool_route_returns_404_for_unknown_tool() -> None:
    with pytest.raises(HTTPException) as exc:
        get_tool("missing.tool")
    assert exc.value.status_code == 404


def test_tool_test_route_runs_echo_handler() -> None:
    result = run_tool_test("local.echo", ToolTestRequest(input_payload={"value": 42}))
    assert result == {"echo": {"value": 42}}


def test_agent_run_route_creates_traceable_run() -> None:
    run = run_agent(
        "research.literature_researcher",
        RunAgentRequest(input_payload={"research_question": "agent governance"}),
    )
    assert run["status"] == "completed"
    assert run["resolved_plan"]["agent_id"] == "research.literature_researcher"
    assert run["artifacts"][0]["metadata"]["run_id"] == run["id"]


def test_domain_registry_unknown_agent_raises_contract_error() -> None:
    with pytest.raises(ContractNotFoundError):
        DomainRegistry.from_default_path().get_agent("unknown.agent")


def test_tool_registry_unknown_tool_raises_contract_error() -> None:
    with pytest.raises(ContractNotFoundError):
        ToolRegistry.from_default_path().get("unknown.tool")


def test_domain_registry_loads_custom_tmp_domain(tmp_path: Path) -> None:
    domain_dir = tmp_path / "demo"
    agents_dir = domain_dir / "agents"
    agents_dir.mkdir(parents=True)
    (domain_dir / "domain.yaml").write_text(
        """
domain_id: demo
name: Demo
version: 0.1.0
status: experimental
agents:
  - demo.agent
tools:
  - local.echo
""".strip()
    )
    (agents_dir / "agent.yaml").write_text(
        """
agent_id: demo.agent
name: Demo Agent
version: 0.1.0
domain: demo
risk_level: low
role: Test role.
goal: Test goal.
input_schema:
  type: object
output_schema:
  type: object
allowed_tools:
  - local.echo
""".strip()
    )
    registry = DomainRegistry.from_directory(tmp_path)
    assert registry.get_domain("demo").agents == ["demo.agent"]
    assert registry.get_agent("demo.agent").name == "Demo Agent"


def test_planner_adds_obsidian_step_only_when_allowed() -> None:
    agent = DomainRegistry.from_default_path().get_agent("research.research_critic")
    plan = SimplePlanner().create_plan(agent)
    assert "write_obsidian_note" not in {step.step_id for step in plan.steps}


def test_planner_includes_agent_approval_points() -> None:
    agent = DomainRegistry.from_default_path().get_agent("cybersecurity.sigma_rule_agent")
    plan = SimplePlanner().create_plan(agent)
    assert "production.deploy_rule" in plan.approval_points


def test_tool_policy_blocks_non_allowlisted_tool() -> None:
    agent = DomainRegistry.from_default_path().get_agent("research.research_critic")
    tool = ToolRegistry.from_default_path().get("obsidian.write_note")
    with pytest.raises(ToolPolicyError):
        ToolPolicy().validate(agent, tool)


def test_tool_executor_creates_pending_approval_for_high_risk_allowed_tool() -> None:
    repository = InMemoryRepository()
    agent = DomainRegistry.from_default_path().get_agent("research.literature_researcher").model_copy(
        update={"allowed_tools": ["shell.execute"], "forbidden_tools": []}
    )
    call = ToolExecutor(ToolRegistry.from_default_path(), repository).execute(
        "run-1", agent, "shell.execute", {"command": "date"}
    )
    assert call["approval_status"] == "pending"
    assert repository.approvals[0]["tool_id"] == "shell.execute"


def test_rag_search_returns_empty_for_no_match() -> None:
    ingestor = DocumentIngestor()
    ingestor.ingest("One", "alpha beta gamma", {})
    assert InMemoryRetriever(ingestor).search("delta") == []


def test_chunker_splits_long_text_into_stable_chunk_ids() -> None:
    chunks = TextChunker().chunk("doc-1", "abcdef", {}, size=2)
    assert [chunk.chunk_id for chunk in chunks] == [
        "doc-1_chunk_0",
        "doc-1_chunk_1",
        "doc-1_chunk_2",
    ]
    assert [chunk.text for chunk in chunks] == ["ab", "cd", "ef"]


def test_embedding_provider_is_deterministic() -> None:
    provider = MockEmbeddingProvider()
    assert provider.embed("same text") == provider.embed("same text")


def test_obsidian_note_writer_sanitizes_path_slashes() -> None:
    note = ObsidianNoteWriter().write_note("Run/With/Slash", "Body")
    assert note["path"] == "00_Inbox/Run-With-Slash.md"


def test_eval_report_summarize_counts_passed_results() -> None:
    summary = summarize(
        [
            {"eval_name": "a", "passed": True, "score": 1.0},
            {"eval_name": "b", "passed": False, "score": 0.0},
            {"eval_name": "a", "passed": True, "score": 0.8},
        ]
    )
    assert summary == {
        "total": 3,
        "passed": 2,
        "failed": 1,
        "pass_rate": 0.667,
        "average_score": 0.6,
        "failed_evaluations": {"b": 1},
    }


def test_artifact_writer_preserves_run_id_metadata() -> None:
    artifact = ArtifactWriter().build_run_trace({"id": "run-123", "status": "completed"})
    assert artifact.name == "run_trace.json"
    assert artifact.metadata == {"run_id": "run-123"}


def test_intent_router_prefers_cybersecurity_keywords() -> None:
    assert IntentRouter().route("Research suspicious Sigma threat behavior") == "cybersecurity"


def test_prompt_renderer_and_validator_use_required_variables() -> None:
    template = "Hello {name}, run {run_id}"
    assert has_required_variables(template, ["name", "run_id"])
    assert render(template, {"name": "Mert", "run_id": "42"}) == "Hello Mert, run 42"


def test_identity_reranker_keeps_order_and_objects() -> None:
    results = [{"chunk_id": "a"}, {"chunk_id": "b"}]
    assert IdentityReranker().rerank(results) is results


def test_agent_contract_defaults_optional_lists() -> None:
    agent = AgentContract.model_validate(
        {
            "agent_id": "minimal.agent",
            "name": "Minimal",
            "version": "0.1.0",
            "domain": "research",
            "role": "Role",
            "goal": "Goal",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
        }
    )
    assert agent.allowed_tools == []
    assert agent.evaluation == []


def test_evals_reports_route_reflects_repository_shape() -> None:
    report = reports()[0]
    assert report["status"] == "ready"
    assert isinstance(report["runs"], int)
    assert {"total", "passed", "failed", "pass_rate", "average_score", "failed_evaluations"} <= set(
        report["summary"]
    )
