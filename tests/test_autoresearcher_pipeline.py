from app.autoresearcher.pipeline import (
    AutoResearcherPipeline,
    AutoresearchDomainImprovementPipeline,
)
from app.autoresearcher.schemas import DomainImprovementTarget


def test_autoresearcher_pipeline_outputs_domain_improvement_artifacts() -> None:
    result = AutoResearcherPipeline().run("cybersecurity")
    assert "program.md" in result
    assert "experiment_plan.json" in result
    assert "measurement_rubric.json" in result
    assert "improvement_backlog.md" in result


def test_autoresearch_domain_improvement_program_constrains_editable_targets() -> None:
    target = DomainImprovementTarget(
        asset_type="agent_contract",
        asset_id="cybersecurity.sigma_rule_agent",
        path="app/domains/cybersecurity/agents/sigma_rule_agent.yaml",
        objective="Improve measurable Sigma output contract quality.",
    )
    plan = AutoresearchDomainImprovementPipeline().plan(
        domain_id="cybersecurity",
        targets=[target],
        budget_minutes=20,
        primary_metric="sigma_eval_pass_rate",
    )

    assert plan.domain_id == "cybersecurity"
    assert plan.budget_minutes == 20
    assert plan.primary_metric == "sigma_eval_pass_rate"
    assert "app/domains/cybersecurity/agents/sigma_rule_agent.yaml" in plan.program_markdown
    assert "Tool governance must not be weakened" in plan.program_markdown


def test_autoresearch_default_targets_are_domain_measurable_assets() -> None:
    plan = AutoresearchDomainImprovementPipeline().plan(domain_id="research", targets=[])
    asset_types = {target.asset_type for target in plan.editable_targets}
    assert {
        "domain_contract",
        "agent_contract",
        "prompt_template",
        "tool_policy",
        "eval_rubric",
    } <= asset_types
    assert "app/domains/research/agents/literature_researcher.yaml" in plan.program_markdown


def test_autoresearch_improvement_run_snapshots_and_scores_assets() -> None:
    run = AutoresearchDomainImprovementPipeline().run_improvement(
        domain_id="cybersecurity",
        targets=[
            DomainImprovementTarget(
                asset_type="domain_contract",
                asset_id="cybersecurity",
                path="app/domains/cybersecurity/domain.yaml",
                objective="Improve cybersecurity domain coverage.",
            )
        ],
        primary_metric="contract_validity",
    )

    assert run.domain_id == "cybersecurity"
    assert run.asset_snapshots[0].exists is True
    assert run.measurement_results[0].name == "contract_validity"
    assert run.keep_decision.decision == "keep"
    assert "keep_discard_decision.json" in run.artifacts


class _FakeRepo:
    """Minimal repository stub exposing just what real_eval_pass_rate needs."""

    def __init__(self, runs: list[dict], evals: dict[str, list[dict]]) -> None:
        self._runs = runs
        self._evals = evals

    def list_runs(self) -> list[dict]:
        return self._runs

    def list_run_evaluations(self, run_id: str) -> list[dict]:
        return self._evals.get(run_id, [])


def test_real_eval_pass_rate_uses_stored_evaluations() -> None:
    repo = _FakeRepo(
        runs=[
            {"id": "r1", "domain_id": "cybersecurity"},
            {"id": "r2", "domain_id": "cybersecurity"},
            {"id": "r3", "domain_id": "research"},  # other domain, ignored
        ],
        evals={
            "r1": [{"eval_name": "a", "passed": True, "score": 1.0},
                   {"eval_name": "b", "passed": False, "score": 0.0}],
            "r2": [{"eval_name": "a", "passed": True, "score": 1.0}],
            "r3": [{"eval_name": "a", "passed": False, "score": 0.0}],
        },
    )
    pipeline = AutoresearchDomainImprovementPipeline(repository=repo)
    result = pipeline.real_eval_pass_rate("cybersecurity")
    assert result is not None
    pass_rate, finding = result
    # 2 of 3 cybersecurity evaluations passed; research run excluded.
    assert pass_rate == round(2 / 3, 3)
    assert "2 run(s)" in finding


def test_real_eval_pass_rate_falls_back_without_data() -> None:
    assert AutoresearchDomainImprovementPipeline().real_eval_pass_rate("cybersecurity") is None
    empty = AutoresearchDomainImprovementPipeline(repository=_FakeRepo([], {}))
    assert empty.real_eval_pass_rate("cybersecurity") is None


def test_improvement_run_uses_real_eval_pass_rate_when_repository_present() -> None:
    repo = _FakeRepo(
        runs=[{"id": "r1", "domain_id": "cybersecurity"}],
        evals={"r1": [{"eval_name": "a", "passed": True, "score": 1.0}]},
    )
    run = AutoresearchDomainImprovementPipeline(repository=repo).run_improvement(
        domain_id="cybersecurity",
        targets=[
            DomainImprovementTarget(
                asset_type="domain_contract",
                asset_id="cybersecurity",
                path="app/domains/cybersecurity/domain.yaml",
                objective="Improve cybersecurity domain coverage.",
            )
        ],
        primary_metric="contract_validity",
    )
    eval_measure = next(m for m in run.measurement_results if m.name == "eval_pass_rate")
    assert eval_measure.score == 1.0
    assert "Real eval pass rate" in eval_measure.finding


def test_autoresearch_improvement_rejects_paths_outside_project() -> None:
    target = DomainImprovementTarget(
        asset_type="prompt_template",
        asset_id="bad",
        path="../outside.md",
        objective="Should be rejected.",
    )

    try:
        AutoresearchDomainImprovementPipeline().run_improvement(
            domain_id="research",
            targets=[target],
        )
    except ValueError as exc:
        assert "escapes project root" in str(exc)
    else:
        raise AssertionError("Expected path escape to fail")
