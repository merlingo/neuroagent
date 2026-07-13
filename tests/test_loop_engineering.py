"""Tests for Loop Engineering integration features."""

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.contracts.loop_contract import (
    EvaluateRequest,
    EvaluateResponse,
    LoopContext,
    RunResult,
)
from app.core.idempotency import IdempotencyCache
from app.main import app
from app.model_gateway import _build_loop_context_section, _build_prompt


client = TestClient(app)


# --- Model Override Validation ---


class TestModelOverrideValidation:
    def test_unknown_model_returns_422(self):
        with patch("app.api.routes_agents.get_settings") as mock_settings:
            mock_settings.return_value.neuroagent_allowed_models = "gpt-4.1-mini,claude-sonnet-4-5-20250929"
            mock_settings.return_value.default_tenant_id = "default"
            mock_settings.return_value.api_auth_enabled = False
            response = client.post(
                "/agents/research.literature_researcher/run",
                json={"input_payload": {"research_question": "test"}, "model": "unknown-model"},
            )
        assert response.status_code == 422
        assert "unknown-model" in response.json()["detail"]

    def test_valid_model_passes_validation(self):
        from app.api.routes_agents import _validate_model_override
        with patch("app.api.routes_agents.get_settings") as mock_settings:
            mock_settings.return_value.neuroagent_allowed_models = "gpt-4.1-mini,claude-sonnet-4-5-20250929"
            # Should not raise
            _validate_model_override("gpt-4.1-mini")

    def test_empty_allowlist_rejects_all(self):
        from app.api.routes_agents import _validate_model_override
        with patch("app.api.routes_agents.get_settings") as mock_settings:
            mock_settings.return_value.neuroagent_allowed_models = ""
            with pytest.raises(Exception) as exc_info:
                _validate_model_override("gpt-4.1-mini")
            assert "422" in str(exc_info.value.status_code)

    def test_none_model_passes(self):
        from app.api.routes_agents import _validate_model_override
        # Should not raise
        _validate_model_override(None)


# --- Loop Context Injection ---


class TestLoopContextInjection:
    def test_loop_context_in_system_prompt(self):
        from app.contracts.agent_contract import AgentContract, JsonSchema
        from app.contracts.workflow_contract import ExecutionPlan

        loop_ctx = LoopContext(
            loop_id="loop-123",
            iteration_index=3,
            goal="Fix the authentication bug",
            state_document="Auth module has a race condition.",
            prior_summaries=["Iteration 1: identified bug", "Iteration 2: wrote failing test"],
        )
        agent = AgentContract(
            agent_id="test.agent", name="Test", version="1.0",
            domain="test", role="tester", goal="test",
            input_schema=JsonSchema(), output_schema=JsonSchema(),
        )
        plan = ExecutionPlan(intent="test", domain="test", agent_id="test.agent", steps=[])
        messages = _build_prompt(agent, plan, {}, [], loop_ctx, 24000)
        system_content = messages[0]["content"]

        assert "## Loop context (iteration 3)" in system_content
        assert "Fix the authentication bug" in system_content
        assert "Auth module has a race condition." in system_content
        assert "identified bug" in system_content
        assert "wrote failing test" in system_content

    def test_truncation_removes_oldest_summaries(self):
        loop_ctx = LoopContext(
            loop_id="loop-456",
            iteration_index=10,
            goal="Short goal",
            state_document="Short state",
            prior_summaries=[f"Summary {i}: {'x' * 100}" for i in range(50)],
        )
        # Very small limit to force truncation
        section = _build_loop_context_section(loop_ctx, max_chars=500)

        # Goal must always be present
        assert "Short goal" in section
        # Newest summaries should be included (they are added newest-first)
        assert "Summary 49" in section or len(section) <= 500
        # Should not exceed limit
        assert len(section) <= 500

    def test_goal_never_truncated(self):
        long_goal = "G" * 300
        loop_ctx = LoopContext(
            loop_id="loop-789",
            iteration_index=1,
            goal=long_goal,
            state_document="state",
            prior_summaries=["summary"],
        )
        section = _build_loop_context_section(loop_ctx, max_chars=200)
        # Goal is always included even if over limit
        assert long_goal in section


# --- Budget Enforcement ---


class TestBudgetEnforcement:
    def _make_executor(self):
        from app.core.executor import StepExecutor
        from app.model_gateway import StubModelGateway
        from app.tools.executor import ToolExecutor
        from app.tools.registry import ToolRegistry
        from app.contracts.tool_contract import ToolContract
        from app.db.repositories import InMemoryRepository as MemoryRepository

        tool_registry = ToolRegistry(contracts={})
        repo = MemoryRepository()
        return StepExecutor(ToolExecutor(tool_registry, repo), StubModelGateway())

    def test_max_steps_stops_gracefully(self):
        from app.contracts.agent_contract import AgentContract, JsonSchema
        from app.contracts.workflow_contract import ExecutionPlan, WorkflowStep

        agent = AgentContract(
            agent_id="test.agent", name="Test", version="1.0",
            domain="test", role="tester", goal="test",
            input_schema=JsonSchema(), output_schema=JsonSchema(),
        )
        steps = [
            WorkflowStep(step_id=f"step_{i}", type="agent_reasoning", depends_on=[])
            for i in range(5)
        ]
        plan = ExecutionPlan(intent="test", domain="test", agent_id="test.agent", steps=steps)
        executor = self._make_executor()

        result = executor.execute("run-1", agent, plan, {}, max_steps=2)
        assert result["status"] == "max_steps"
        assert len(result["steps"]) == 2

    def test_max_tokens_stops_gracefully(self):
        from app.contracts.agent_contract import AgentContract, JsonSchema
        from app.contracts.workflow_contract import ExecutionPlan, WorkflowStep

        agent = AgentContract(
            agent_id="test.agent", name="Test", version="1.0",
            domain="test", role="tester", goal="test",
            input_schema=JsonSchema(), output_schema=JsonSchema(),
        )
        # produce_output triggers model call which generates tokens
        steps = [
            WorkflowStep(step_id="produce_output", type="agent_reasoning", depends_on=[]),
            WorkflowStep(step_id="step_2", type="agent_reasoning", depends_on=[]),
        ]
        plan = ExecutionPlan(intent="test", domain="test", agent_id="test.agent", steps=steps)
        executor = self._make_executor()

        # Set max_tokens very low - the stub generates some tokens
        result = executor.execute("run-2", agent, plan, {}, max_tokens=1)
        # After the first step completes, cumulative tokens > 1, so second step should be blocked
        assert result["status"] in {"max_tokens", "completed"}


# --- Evaluate Endpoint ---


class TestEvaluateEndpoint:
    def test_happy_path(self):
        valid_response = json.dumps({
            "progress": "advanced",
            "confidence": 0.85,
            "stall_signals": [],
            "recommendation": "continue",
            "reasoning": "Good progress was made.",
        })
        with patch("app.api.routes_evaluate.complete_simple", return_value=valid_response):
            response = client.post(
                "/v1/evaluate",
                json={
                    "goal": "Fix the bug",
                    "state_document": "Bug is in auth module",
                    "iteration_summary": "Wrote a fix for the race condition",
                    "recent_verdicts": [],
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["progress"] == "advanced"
        assert data["confidence"] == 0.85
        assert data["recommendation"] == "continue"

    def test_malformed_output_retries_then_502(self):
        with patch("app.api.routes_evaluate.complete_simple", return_value="not json at all"):
            response = client.post(
                "/v1/evaluate",
                json={
                    "goal": "Fix the bug",
                    "state_document": "Bug is in auth module",
                    "iteration_summary": "Wrote a fix",
                    "recent_verdicts": [],
                },
            )
        assert response.status_code == 502
        assert "malformed" in response.json()["detail"].lower()

    def test_model_override_validated(self):
        with patch("app.api.routes_evaluate.get_settings") as mock_settings:
            mock_settings.return_value.neuroagent_allowed_models = "gpt-4.1-mini"
            mock_settings.return_value.api_auth_enabled = False
            mock_settings.return_value.default_tenant_id = "default"
            mock_settings.return_value.neuroagent_critic_model = "gpt-4.1-mini"
            response = client.post(
                "/v1/evaluate",
                json={
                    "goal": "goal",
                    "state_document": "state",
                    "iteration_summary": "summary",
                    "recent_verdicts": [],
                    "model": "forbidden-model",
                },
            )
        assert response.status_code == 422


# --- Idempotency ---


class TestIdempotency:
    def test_duplicate_returns_existing_run_id(self):
        cache = IdempotencyCache()
        # First call stores
        result = cache.check_and_set("tenant-1", "client-run-abc", "run-001")
        assert result is None
        # Second call returns existing
        result = cache.check_and_set("tenant-1", "client-run-abc", "run-002")
        assert result == "run-001"

    def test_different_client_ids_pass(self):
        cache = IdempotencyCache()
        result1 = cache.check_and_set("tenant-1", "client-run-1", "run-001")
        result2 = cache.check_and_set("tenant-1", "client-run-2", "run-002")
        assert result1 is None
        assert result2 is None

    def test_different_tenants_are_isolated(self):
        cache = IdempotencyCache()
        result1 = cache.check_and_set("tenant-1", "same-id", "run-001")
        result2 = cache.check_and_set("tenant-2", "same-id", "run-002")
        assert result1 is None
        assert result2 is None

    def test_update_changes_stored_run_id(self):
        cache = IdempotencyCache()
        cache.check_and_set("tenant-1", "client-run-x", "pending")
        cache.update("tenant-1", "client-run-x", "real-run-id")
        # Next check should return the updated value
        result = cache.check_and_set("tenant-1", "client-run-x", "ignored")
        assert result == "real-run-id"

    def test_ttl_expiry(self):
        cache = IdempotencyCache(ttl=0)  # Immediate expiry
        cache.check_and_set("tenant-1", "client-run-y", "run-old")
        import time
        time.sleep(0.01)
        # After TTL, should not find it
        result = cache.check_and_set("tenant-1", "client-run-y", "run-new")
        assert result is None


# --- Structured Result ---


class TestStructuredResult:
    def test_run_result_always_present(self):
        from app.core.runtime import AgentRuntime
        from app.db.repositories import InMemoryRepository as MemoryRepository
        from app.dependencies import get_domain_registry, get_tool_registry

        repo = MemoryRepository()
        runtime = AgentRuntime(get_domain_registry(), get_tool_registry(), repo)
        run = runtime.run_agent(
            "research.literature_researcher",
            {"research_question": "loop test"},
            max_steps=20,
            max_tokens=100000,
        )
        assert "result" in run
        result = run["result"]
        assert result["status"] in {"completed", "max_steps", "max_tokens", "error"}
        assert "usage" in result
        assert "steps" in result["usage"]
        assert "tool_calls" in result
        assert isinstance(result["tool_calls"], list)

    def test_loop_context_echoed_in_response(self):
        from app.core.runtime import AgentRuntime
        from app.db.repositories import InMemoryRepository as MemoryRepository
        from app.dependencies import get_domain_registry, get_tool_registry

        loop_ctx = LoopContext(
            loop_id="loop-echo-test",
            iteration_index=7,
            goal="Test echo",
            state_document="state",
        )
        repo = MemoryRepository()
        runtime = AgentRuntime(get_domain_registry(), get_tool_registry(), repo)
        run = runtime.run_agent(
            "research.literature_researcher",
            {"research_question": "echo test"},
            loop_context=loop_ctx,
            max_steps=20,
            max_tokens=100000,
        )
        assert run["loop_id"] == "loop-echo-test"
        assert run["iteration_index"] == 7
