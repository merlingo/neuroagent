import hashlib
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from app.autoresearcher.schemas import (
    AutoresearchAssetSnapshot,
    AutoresearchExperimentPlan,
    AutoresearchImprovementRun,
    AutoresearchKeepDecision,
    AutoresearchMeasurementResult,
    DomainImprovementTarget,
    DomainMeasurement,
)
from app.contracts.agent_contract import AgentContract
from app.contracts.domain_contract import DomainContract
from app.evals.reports import summarize


DEFAULT_MEASUREMENTS = [
    DomainMeasurement(
        name="contract_validity",
        description="All edited contracts validate against their Pydantic/YAML schemas.",
        target=1.0,
    ),
    DomainMeasurement(
        name="eval_pass_rate",
        description="Fraction of domain eval tests passing after the proposed change.",
        target=0.95,
    ),
    DomainMeasurement(
        name="trace_completeness",
        description="Agent runs preserve input, plan, tool calls, artifacts, and eval records.",
        target=1.0,
    ),
]


class AutoresearchDomainImprovementPipeline:
    """Plan Karpathy-style autoresearch loops for NeuroAgent domain assets.

    This layer is not a literature-review workflow. It adapts the core idea of
    Karpathy's autoresearch: give an agent a compact instruction program,
    constrain what it can edit, run fixed-budget experiments, score measurable
    results, and keep or discard changes based on the metric.

    When constructed with a ``repository`` the ``eval_pass_rate`` measurement is
    computed from real stored evaluations of the domain's runs instead of the
    asset-existence proxy. Without one (e.g. planning-only, tests) it falls back
    to the proxy so behaviour is unchanged.
    """

    def __init__(self, repository: Any | None = None) -> None:
        self.repository = repository

    def plan(
        self,
        domain_id: str,
        targets: list[DomainImprovementTarget],
        budget_minutes: int = 30,
        primary_metric: str = "eval_pass_rate",
    ) -> AutoresearchExperimentPlan:
        if not targets:
            targets = self.default_targets(domain_id)
        program = self.render_program(domain_id, targets, budget_minutes, primary_metric)
        artifacts: dict[str, str | dict | list] = {
            "program.md": program,
            "experiment_plan.json": {
                "domain_id": domain_id,
                "budget_minutes": budget_minutes,
                "primary_metric": primary_metric,
                "target_count": len(targets),
            },
            "measurement_rubric.json": [
                measurement.model_dump() for measurement in DEFAULT_MEASUREMENTS
            ],
            "improvement_backlog.md": self.render_backlog(targets),
        }
        return AutoresearchExperimentPlan(
            domain_id=domain_id,
            budget_minutes=budget_minutes,
            editable_targets=targets,
            fixed_context=[
                "app/contracts",
                "app/domains/registry.py",
                "app/tools/policy.py",
                "tests",
            ],
            primary_metric=primary_metric,
            acceptance_rule=(
                "Keep a change only when contract validation passes and the primary metric "
                "improves or remains equal with lower complexity."
            ),
            program_markdown=program,
            artifacts=artifacts,
        )

    def run_improvement(
        self,
        domain_id: str,
        targets: list[DomainImprovementTarget],
        budget_minutes: int = 30,
        primary_metric: str = "eval_pass_rate",
        project_root: Path | str = ".",
    ) -> AutoresearchImprovementRun:
        root = Path(project_root).resolve()
        plan = self.plan(
            domain_id=domain_id,
            targets=targets,
            budget_minutes=budget_minutes,
            primary_metric=primary_metric,
        )
        snapshots = [self.snapshot_asset(target, root) for target in plan.editable_targets]
        measurements = self.measure(plan, snapshots, root)
        decision = self.decide(plan.primary_metric, measurements)
        artifacts: dict[str, str | dict[str, Any] | list[Any]] = {
            **plan.artifacts,
            "asset_snapshots.json": [snapshot.model_dump() for snapshot in snapshots],
            "measurement_results.json": [result.model_dump() for result in measurements],
            "metric_comparison.json": self.metric_comparison(measurements),
            "keep_discard_decision.json": decision.model_dump(),
        }
        return AutoresearchImprovementRun(
            run_id=f"autoresearch-{uuid4().hex}",
            domain_id=domain_id,
            plan=plan,
            asset_snapshots=snapshots,
            measurement_results=measurements,
            keep_decision=decision,
            artifacts=artifacts,
        )

    def default_targets(self, domain_id: str) -> list[DomainImprovementTarget]:
        targets = [
            DomainImprovementTarget(
                asset_type="domain_contract",
                asset_id=domain_id,
                path=f"app/domains/{domain_id}/domain.yaml",
                objective="Improve domain task coverage while preserving tool governance.",
                measurements=DEFAULT_MEASUREMENTS,
            ),
        ]
        agent_root = Path("app/domains") / domain_id / "agents"
        for agent_file in sorted(agent_root.glob("*.yaml")):
            targets.append(
                DomainImprovementTarget(
                    asset_type="agent_contract",
                    asset_id=f"{domain_id}.{agent_file.stem}",
                    path=str(agent_file),
                    objective=(
                        "Improve the agent contract, schemas, allowed tools, "
                        "and evaluation mapping."
                    ),
                    measurements=DEFAULT_MEASUREMENTS,
                )
            )
        for prompt_file in sorted(Path("app/prompts/templates").glob("*.md")):
            targets.append(
                DomainImprovementTarget(
                    asset_type="prompt_template",
                    asset_id=f"prompt.{prompt_file.stem}",
                    path=str(prompt_file),
                    objective=(
                        "Improve reusable prompt structure without weakening output constraints."
                    ),
                    measurements=DEFAULT_MEASUREMENTS,
                )
            )
        targets.extend(
            [
                DomainImprovementTarget(
                    asset_type="tool_policy",
                    asset_id="tool_registry_policy",
                    path="app/tools/tools.yaml",
                    objective=(
                        "Improve tool metadata and governance clarity without broadening "
                        "risky access."
                    ),
                    measurements=DEFAULT_MEASUREMENTS,
                ),
                DomainImprovementTarget(
                    asset_type="eval_rubric",
                    asset_id=f"{domain_id}.eval_rubric",
                    path="app/evals/validators.py",
                    objective="Improve measurable eval coverage for the domain stack.",
                    measurements=DEFAULT_MEASUREMENTS,
                ),
            ]
        )
        return targets

    def snapshot_asset(
        self,
        target: DomainImprovementTarget,
        root: Path,
    ) -> AutoresearchAssetSnapshot:
        asset_path = self.resolve_target_path(target.path, root)
        if not asset_path.exists():
            return AutoresearchAssetSnapshot(
                target=target,
                exists=False,
                summary=f"Target path does not exist: {target.path}",
            )
        content = asset_path.read_bytes()
        return AutoresearchAssetSnapshot(
            target=target,
            exists=True,
            content_hash=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
            summary=self.summarize_asset(target, asset_path, content),
        )

    def measure(
        self,
        plan: AutoresearchExperimentPlan,
        snapshots: list[AutoresearchAssetSnapshot],
        root: Path,
    ) -> list[AutoresearchMeasurementResult]:
        validity_score, validity_findings = self.contract_validity_score(snapshots, root)
        trace_score = self.trace_completeness_score(plan.fixed_context, root)

        real = self.real_eval_pass_rate(plan.domain_id)
        if real is not None:
            eval_score, eval_finding = real
        else:
            eval_score = self.eval_pass_rate_proxy(snapshots)
            eval_finding = (
                "Proxy score based on existing, parseable improvement targets "
                "(no stored evaluations for this domain yet)."
            )

        scores = {
            "contract_validity": (validity_score, "; ".join(validity_findings)),
            "eval_pass_rate": (eval_score, eval_finding),
            "trace_completeness": (
                trace_score,
                "Fixed runtime context paths are available for review.",
            ),
        }
        measurements = list(DEFAULT_MEASUREMENTS)
        if plan.primary_metric not in scores:
            measurements.append(
                DomainMeasurement(
                    name=plan.primary_metric,
                    description=(
                        "Custom primary metric mapped to the current eval proxy until "
                        "a concrete evaluator is registered."
                    ),
                    target=0.95,
                )
            )
            scores[plan.primary_metric] = scores["eval_pass_rate"]
        return [
            self.measurement_result(measurement, *scores[measurement.name])
            for measurement in measurements
            if measurement.name in scores
        ]

    def decide(
        self,
        primary_metric: str,
        measurements: list[AutoresearchMeasurementResult],
    ) -> AutoresearchKeepDecision:
        by_name = {result.name: result for result in measurements}
        validity = by_name.get("contract_validity")
        primary = by_name.get(primary_metric) or by_name.get("eval_pass_rate")
        if validity and not validity.passed:
            return AutoresearchKeepDecision(
                decision="discard",
                primary_metric=primary_metric,
                baseline=primary.baseline if primary else None,
                score=primary.score if primary else None,
                delta=self.delta(primary),
                reason="Contract or asset validation failed.",
            )
        if primary and primary.passed:
            return AutoresearchKeepDecision(
                decision="keep",
                primary_metric=primary_metric,
                baseline=primary.baseline,
                score=primary.score,
                delta=self.delta(primary),
                reason=(
                    "Primary metric met the configured acceptance target and required "
                    "assets validated."
                ),
            )
        return AutoresearchKeepDecision(
            decision="needs_review",
            primary_metric=primary_metric,
            baseline=primary.baseline if primary else None,
            score=primary.score if primary else None,
            delta=self.delta(primary),
            reason=(
                "The improvement package is measurable but did not meet the automatic "
                "keep threshold."
            ),
        )

    def metric_comparison(
        self,
        measurements: list[AutoresearchMeasurementResult],
    ) -> dict[str, dict[str, float | bool | None]]:
        return {
            result.name: {
                "baseline": result.baseline,
                "score": result.score,
                "target": result.target,
                "delta": self.delta(result),
                "passed": result.passed,
            }
            for result in measurements
        }

    def resolve_target_path(self, path: str, root: Path) -> Path:
        candidate = (root / path).resolve()
        if candidate != root and root not in candidate.parents:
            raise ValueError(f"Autoresearch target path escapes project root: {path}")
        return candidate

    def summarize_asset(self, target: DomainImprovementTarget, path: Path, content: bytes) -> str:
        if target.asset_type in {"agent_contract", "domain_contract", "tool_policy"}:
            data = yaml.safe_load(content.decode("utf-8")) or {}
            if isinstance(data, dict):
                keys = ", ".join(sorted(data.keys())[:8])
                return f"YAML asset with keys: {keys}"
        if target.asset_type == "prompt_template":
            return f"Prompt template with {len(content.decode('utf-8').split())} words."
        if target.asset_type == "eval_rubric":
            return f"Evaluation asset with {len(content.decode('utf-8').splitlines())} lines."
        return f"Asset size: {len(content)} bytes."

    def contract_validity_score(
        self,
        snapshots: list[AutoresearchAssetSnapshot],
        root: Path,
    ) -> tuple[float, list[str]]:
        findings: list[str] = []
        valid_count = 0
        for snapshot in snapshots:
            target = snapshot.target
            if not snapshot.exists:
                findings.append(f"{target.path}: missing")
                continue
            try:
                path = self.resolve_target_path(target.path, root)
                self.validate_asset(target, path)
            except Exception as exc:
                findings.append(f"{target.path}: invalid ({exc})")
                continue
            findings.append(f"{target.path}: valid")
            valid_count += 1
        if not snapshots:
            return 0.0, ["No editable targets were provided."]
        return valid_count / len(snapshots), findings

    def validate_asset(self, target: DomainImprovementTarget, path: Path) -> None:
        if target.asset_type == "domain_contract":
            DomainContract.model_validate(yaml.safe_load(path.read_text()))
            return
        if target.asset_type == "agent_contract":
            AgentContract.model_validate(yaml.safe_load(path.read_text()))
            return
        if target.asset_type == "tool_policy":
            yaml.safe_load(path.read_text())
            return
        if target.asset_type in {"prompt_template", "eval_rubric"}:
            if not path.read_text().strip():
                raise ValueError("asset is empty")

    def real_eval_pass_rate(self, domain_id: str) -> tuple[float, str] | None:
        """Real eval pass rate for a domain, computed from stored evaluations of
        its runs. Returns None when no repository is wired or no evaluations exist
        yet, so the caller can fall back to the proxy."""
        if self.repository is None:
            return None
        try:
            runs = [run for run in self.repository.list_runs() if run.get("domain_id") == domain_id]
            evaluations: list[dict[str, Any]] = []
            for run in runs:
                evaluations.extend(self.repository.list_run_evaluations(run["id"]))
        except Exception:
            return None
        if not evaluations:
            return None
        stats = summarize(evaluations)
        finding = (
            f"Real eval pass rate over {stats['total']} evaluation(s) across "
            f"{len(runs)} run(s): {stats['passed']} passed, {stats['failed']} failed "
            f"(avg score {stats['average_score']})."
        )
        return stats["pass_rate"], finding

    def eval_pass_rate_proxy(self, snapshots: list[AutoresearchAssetSnapshot]) -> float:
        if not snapshots:
            return 0.0
        existing = sum(1 for snapshot in snapshots if snapshot.exists)
        return existing / len(snapshots)

    def trace_completeness_score(self, fixed_context: list[str], root: Path) -> float:
        if not fixed_context:
            return 1.0
        available = sum(
            1 for path in fixed_context if self.resolve_target_path(path, root).exists()
        )
        return available / len(fixed_context)

    def measurement_result(
        self,
        measurement: DomainMeasurement,
        score: float,
        finding: str,
    ) -> AutoresearchMeasurementResult:
        baseline = measurement.baseline if measurement.baseline is not None else 0.0
        target = measurement.target
        if target is None:
            passed = score >= baseline if measurement.higher_is_better else score <= baseline
        elif measurement.higher_is_better:
            passed = score >= target
        else:
            passed = score <= target
        return AutoresearchMeasurementResult(
            name=measurement.name,
            score=round(score, 4),
            passed=passed,
            higher_is_better=measurement.higher_is_better,
            baseline=baseline,
            target=target,
            finding=finding,
        )

    def delta(self, result: AutoresearchMeasurementResult | None) -> float | None:
        if result is None or result.baseline is None:
            return None
        return round(result.score - result.baseline, 4)

    def render_program(
        self,
        domain_id: str,
        targets: list[DomainImprovementTarget],
        budget_minutes: int,
        primary_metric: str,
    ) -> str:
        editable = "\n".join(f"- `{target.path}`: {target.objective}" for target in targets)
        metrics = "\n".join(
            f"- `{measurement.name}`: {measurement.description}"
            for measurement in DEFAULT_MEASUREMENTS
        )
        return f"""# Autoresearch Program: {domain_id}

You are running a fixed-budget improvement loop for NeuroAgent domain assets.

## Objective

Improve measurable domain quality for `{domain_id}` by editing only explicitly allowed assets.

## Editable Targets

{editable}

## Fixed Context

- Core runtime contracts are not the experiment target.
- Tool governance must not be weakened.
- Existing tests must continue to pass.
- New tests must be added for any changed measurable behavior.

## Budget

- Time budget: {budget_minutes} minutes.
- Optimize for small, reviewable diffs.
- Stop when the budget is exhausted or no metric-improving change is available.

## Metrics

Primary metric: `{primary_metric}`

{metrics}

## Acceptance Rule

Keep a change only if it validates and improves the primary metric, or keeps the primary metric
equal while reducing complexity or increasing coverage.

## Output Required

- Proposed patch summary.
- Metric before/after table.
- Tests added or updated.
- Keep/discard decision with reason.
"""

    def render_backlog(self, targets: list[DomainImprovementTarget]) -> str:
        lines = ["# Domain Improvement Backlog", ""]
        for target in targets:
            lines.append(f"- [{target.asset_type}] `{target.asset_id}` at `{target.path}`")
            lines.append(f"  Objective: {target.objective}")
        return "\n".join(lines) + "\n"


class AutoResearcherPipeline(AutoresearchDomainImprovementPipeline):
    """Backward-compatible name for the domain improvement pipeline."""

    def run(self, domain_id: str) -> dict:
        plan = self.plan(domain_id=domain_id, targets=[])
        return plan.artifacts
