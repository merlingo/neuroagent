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
