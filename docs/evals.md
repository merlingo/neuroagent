# Evaluations

Evaluations are deterministic runtime checks attached to every agent run. They are not a second
model call. The evaluation layer inspects the persisted run, final output, tool-call trace, approval
state, and the agent contract, then stores one `EvaluationResult` per check.

## Default Checks

Every run receives these checks:

- `no_empty_answer`: final output must be present and non-empty.
- `output_schema_valid`: final output must satisfy the agent output schema.
- `tool_policy_respected`: executed tools must not violate allowlists, forbidden tools, domain policy,
  or policy-error signals.
- `approval_rules_respected`: approval-gated tools must stop with `pending` or `approved` state.

## Contract Checks

Agents can add domain-specific checks in their YAML `evaluation` list. Current registered checks are:

- `evidence_required`
- `claims_have_evidence`
- `limitations_present`
- `false_positive_analysis_present`
- `sigma_yaml_valid`
- `yara_rule_valid`
- `mitre_mapping_present`
- `counterarguments_present`
- `experiment_plan_present`

Unknown evaluation names fail explicitly so contract drift is visible instead of silently passing.

## Reports

`GET /evals/reports` summarizes persisted evaluation records across repository runs. The report
includes total checks, pass/fail counts, pass rate, average score, and failed-evaluation counts.
