import pytest
from fastapi import HTTPException

from app.api.routes_autoresearch import (
    AutoresearchPlanRequest,
    create_improvement_run,
    create_plan,
    default_targets,
)
from app.autoresearcher.schemas import DomainImprovementTarget
from app.main import app


def test_autoresearch_routes_are_registered() -> None:
    paths = {route.path for route in app.routes}
    assert "/autoresearch/domains/{domain_id}/targets" in paths
    assert "/autoresearch/domains/{domain_id}/plan" in paths
    assert "/autoresearch/domains/{domain_id}/improvement-run" in paths


def test_default_targets_endpoint_returns_measurable_domain_assets() -> None:
    targets = default_targets("cybersecurity")
    asset_types = {target["asset_type"] for target in targets}
    assert {
        "domain_contract",
        "agent_contract",
        "prompt_template",
        "tool_policy",
        "eval_rubric",
    } <= asset_types
    assert any(target["path"].startswith("app/domains/cybersecurity") for target in targets)


def test_default_targets_endpoint_rejects_unknown_domain() -> None:
    with pytest.raises(HTTPException) as exc:
        default_targets("unknown")
    assert exc.value.status_code == 404


def test_create_plan_endpoint_generates_program_markdown_with_custom_target() -> None:
    request = AutoresearchPlanRequest(
        budget_minutes=15,
        primary_metric="contract_validity",
        targets=[
            DomainImprovementTarget(
                asset_type="prompt_template",
                asset_id="cybersecurity.sigma.prompt",
                path="app/domains/cybersecurity/prompts/sigma.md",
                objective="Improve Sigma prompt measurability.",
            )
        ],
    )
    plan = create_plan("cybersecurity", request)
    assert plan["budget_minutes"] == 15
    assert plan["primary_metric"] == "contract_validity"
    assert "program.md" in plan["artifacts"]
    assert "app/domains/cybersecurity/prompts/sigma.md" in plan["program_markdown"]


def test_create_plan_endpoint_rejects_unknown_domain() -> None:
    with pytest.raises(HTTPException) as exc:
        create_plan("unknown", AutoresearchPlanRequest())
    assert exc.value.status_code == 404


def test_create_improvement_run_endpoint_returns_keep_discard_package() -> None:
    run = create_improvement_run(
        "cybersecurity",
        AutoresearchPlanRequest(
            primary_metric="contract_validity",
            targets=[
                DomainImprovementTarget(
                    asset_type="domain_contract",
                    asset_id="cybersecurity",
                    path="app/domains/cybersecurity/domain.yaml",
                    objective="Improve cybersecurity domain coverage.",
                )
            ],
        ),
    )

    assert run["keep_decision"]["decision"] == "keep"
    assert run["asset_snapshots"][0]["exists"] is True
    assert "metric_comparison.json" in run["artifacts"]


def test_create_improvement_run_endpoint_rejects_path_escape() -> None:
    with pytest.raises(HTTPException) as exc:
        create_improvement_run(
            "cybersecurity",
            AutoresearchPlanRequest(
                targets=[
                    DomainImprovementTarget(
                        asset_type="prompt_template",
                        asset_id="bad",
                        path="../outside.md",
                        objective="Should be rejected.",
                    )
                ]
            ),
        )
    assert exc.value.status_code == 400
