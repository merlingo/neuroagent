# Autoresearch Layer

This layer adapts Karpathy's `autoresearch` idea for NeuroAgent domain-stack improvement.

It is not a literature-review product layer. It is an internal domain improvement subsystem for measurable assets such as:

- agent contracts
- prompt templates
- domain contracts
- tool policies
- eval rubrics

## Reference Model

Karpathy's `autoresearch` uses a compact `program.md` instruction file, a constrained editable surface, a fixed experiment budget, and a measurable metric to decide whether agent-proposed changes should be kept or discarded.

NeuroAgent applies the same pattern to domain quality:

```text
domain stack + measurable target + program.md + fixed budget + eval metric
```

## NeuroAgent Adaptation

Instead of letting an agent modify model training code, NeuroAgent gives the agent a constrained set of domain assets to improve.

Examples:

| Asset | Example target |
|---|---|
| Agent contract | tighten input/output schemas |
| Prompt template | improve instruction clarity |
| Domain contract | improve supported task coverage |
| Tool policy | improve governance without weakening controls |
| Eval rubric | add missing measurable checks |

## Outputs

The planning endpoint produces:

- `program.md`
- `experiment_plan.json`
- `measurement_rubric.json`
- `improvement_backlog.md`

The improvement-run endpoint adds:

- `asset_snapshots.json`
- `measurement_results.json`
- `metric_comparison.json`
- `keep_discard_decision.json`

## Framework Usage

Use the layer in three levels:

1. Inspect the editable boundary:

```bash
curl http://127.0.0.1:8011/autoresearch/domains/cybersecurity/targets
```

2. Generate the fixed-budget program without running measurements:

```bash
curl -X POST http://127.0.0.1:8011/autoresearch/domains/cybersecurity/plan \
  -H 'Content-Type: application/json' \
  -d '{"budget_minutes": 30, "primary_metric": "eval_pass_rate"}'
```

3. Build a measurable improvement package:

```bash
curl -X POST http://127.0.0.1:8011/autoresearch/domains/cybersecurity/improvement-run \
  -H 'Content-Type: application/json' \
  -d '{"budget_minutes": 30, "primary_metric": "contract_validity"}'
```

The improvement run does not write arbitrary project files. It snapshots target assets, validates
contracts and parseable assets, computes deterministic measurement results, and returns a
`keep`, `discard`, or `needs_review` decision. Candidate patches should still be applied through
the normal review workflow.

## Acceptance Rule

Keep a change only when:

- contract validation passes,
- existing tests pass,
- relevant domain evals pass,
- the primary metric improves, or remains equal with lower complexity/higher coverage.
