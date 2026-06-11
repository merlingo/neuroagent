from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from app.contracts.agent_contract import AgentContract
from app.contracts.validation import validate_payload
from app.evals.rubric import EvalOutcome, failed, passed


EvaluationValidator = Callable[[AgentContract, dict[str, Any]], EvalOutcome]


def no_empty_answer(agent: AgentContract, run: dict[str, Any]) -> EvalOutcome:
    output = _final_output(run)
    if isinstance(output, dict) and output:
        return passed("Final output must not be empty.", ["Final output is present."])
    return failed(
        "Final output must not be empty.",
        [_run_context(run), "final_output is missing or empty."],
    )


def output_schema_valid(agent: AgentContract, run: dict[str, Any]) -> EvalOutcome:
    output = _final_output(run)
    if not isinstance(output, dict):
        return failed(
            "Final output must satisfy the agent output schema.",
            [_run_context(run), "final_output is not an object."],
        )
    try:
        validate_payload(agent.output_schema, output, "agent output")
    except Exception as exc:
        return failed("Final output must satisfy the agent output schema.", [str(exc)])
    return passed("Final output must satisfy the agent output schema.", ["Output schema validation passed."])


def tool_policy_respected(agent: AgentContract, run: dict[str, Any]) -> EvalOutcome:
    findings: list[str] = []
    violations = 0
    for call in _tool_calls(run):
        tool_name = call.get("tool_name")
        if call.get("error_message"):
            violations += 1
            findings.append(f"{tool_name} returned error: {call['error_message']}")
        if tool_name in agent.forbidden_tools:
            violations += 1
            findings.append(f"{tool_name} is forbidden for {agent.agent_id}.")
        if agent.allowed_tools and tool_name not in agent.allowed_tools:
            violations += 1
            findings.append(f"{tool_name} is not allowlisted for {agent.agent_id}.")

    error_message = str(run.get("error_message") or "")
    if _looks_like_tool_policy_error(error_message):
        violations += 1
        findings.append(f"Run error indicates a tool policy violation: {error_message}")

    if violations:
        return failed(
            "Tool calls must respect allowed, forbidden, and approval policies.",
            findings,
            score=0.0,
        )
    if not _tool_calls(run):
        findings.append("No tool calls were executed.")
    return passed("Tool calls must respect allowed, forbidden, and approval policies.", findings)


def approval_rules_respected(agent: AgentContract, run: dict[str, Any]) -> EvalOutcome:
    findings: list[str] = []
    violations = 0
    for call in _tool_calls(run):
        tool_name = call.get("tool_name")
        requires_approval = bool(call.get("approval_required")) or tool_name in agent.human_approval_required_for
        if not requires_approval:
            continue
        approval_status = call.get("approval_status")
        if approval_status not in {"pending", "approved"}:
            violations += 1
            findings.append(f"{tool_name} required approval but status was {approval_status!r}.")
    if violations:
        return failed("Approval-gated tools must stop for human approval before execution.", findings)
    return passed("Approval-gated tools must stop for human approval before execution.", findings or ["No approval violations found."])


def evidence_required(agent: AgentContract, run: dict[str, Any]) -> EvalOutcome:
    evidence = _evidence_items(run)
    if evidence:
        return passed("Evidence-grounded agents must return at least one evidence item.", [f"Found {len(evidence)} evidence item(s)."])
    return failed("Evidence-grounded agents must return at least one evidence item.", ["final_output.evidence is empty."])


def claims_have_evidence(agent: AgentContract, run: dict[str, Any]) -> EvalOutcome:
    output = _final_output(run)
    summary = str(output.get("summary", "")) if isinstance(output, dict) else ""
    evidence = _evidence_items(run)
    if summary.strip() and evidence:
        return passed("Claims in the summary must be backed by evidence records.", ["Summary and evidence are both present."])
    findings = []
    if not summary.strip():
        findings.append("summary is missing or empty.")
    if not evidence:
        findings.append("evidence is missing or empty.")
    return failed("Claims in the summary must be backed by evidence records.", findings)


def limitations_present(agent: AgentContract, run: dict[str, Any]) -> EvalOutcome:
    output = _final_output(run)
    if isinstance(output, dict) and output.get("open_questions"):
        return passed("Research outputs must include limitations, assumptions, or open questions.", ["open_questions is present."])
    text = _as_text(output)
    if _contains_any(text, ["limitation", "limitations", "assumption", "assumptions", "caveat", "unknown", "uncertain"]):
        return passed("Research outputs must include limitations, assumptions, or open questions.", ["Limitation language was found."])
    return failed("Research outputs must include limitations, assumptions, or open questions.", ["No limitation, assumption, caveat, unknown, or open-question signal found."])


def false_positive_analysis_present(agent: AgentContract, run: dict[str, Any]) -> EvalOutcome:
    output = _final_output(run)
    if isinstance(output, dict) and _non_empty(output.get("false_positive_analysis")):
        return passed("Detection outputs must include false-positive analysis.", ["false_positive_analysis is present."])
    if _contains_any(_as_text(output), ["false positive", "false-positive", "noise", "benign"]):
        return passed("Detection outputs must include false-positive analysis.", ["False-positive language was found."])
    return failed("Detection outputs must include false-positive analysis.", ["No false-positive analysis found."])


def sigma_yaml_valid(agent: AgentContract, run: dict[str, Any]) -> EvalOutcome:
    output = _final_output(run)
    sigma_rule = output.get("sigma_rule") if isinstance(output, dict) else None
    if not isinstance(sigma_rule, dict):
        return failed("Sigma output must include a minimally valid Sigma rule object.", ["sigma_rule is missing or not an object."])
    missing = [field for field in ["title", "logsource", "detection"] if field not in sigma_rule]
    detection = sigma_rule.get("detection")
    if isinstance(detection, dict) and "condition" not in detection:
        missing.append("detection.condition")
    if missing:
        return failed("Sigma output must include a minimally valid Sigma rule object.", [f"Missing field(s): {', '.join(missing)}"])
    return passed("Sigma output must include a minimally valid Sigma rule object.", ["Sigma rule has title, logsource, detection, and condition."])


def yara_rule_valid(agent: AgentContract, run: dict[str, Any]) -> EvalOutcome:
    output = _final_output(run)
    candidate = ""
    if isinstance(output, dict):
        candidate = str(output.get("yara_rule") or output.get("rule") or output.get("summary") or "")
    candidate += "\n" + _as_text(output)
    if re.search(r"\brule\s+[A-Za-z_][A-Za-z0-9_]*\s*\{", candidate) and "condition:" in candidate:
        return passed("YARA output must include a rule declaration and condition block.", ["YARA rule syntax markers were found."])
    return failed("YARA output must include a rule declaration and condition block.", ["No YARA rule declaration with a condition block found."])


def mitre_mapping_present(agent: AgentContract, run: dict[str, Any]) -> EvalOutcome:
    output = _final_output(run)
    if isinstance(output, dict):
        for key in ["mitre_attack", "mitre_mapping", "attack_techniques", "techniques"]:
            if _non_empty(output.get(key)):
                return passed("Threat research must include MITRE ATT&CK mapping signals.", [f"{key} is present."])
    text = _as_text(output)
    if re.search(r"\bT\d{4}(?:\.\d{3})?\b", text) or _contains_any(text, ["mitre", "att&ck", "attack technique"]):
        return passed("Threat research must include MITRE ATT&CK mapping signals.", ["MITRE/ATT&CK language or technique IDs were found."])
    return failed("Threat research must include MITRE ATT&CK mapping signals.", ["No MITRE ATT&CK mapping signal found."])


def counterarguments_present(agent: AgentContract, run: dict[str, Any]) -> EvalOutcome:
    output = _final_output(run)
    if isinstance(output, dict) and _non_empty(output.get("counterarguments")):
        return passed("Hypothesis outputs must include counterarguments or alternatives.", ["counterarguments is present."])
    if _contains_any(_as_text(output), ["counterargument", "counter-argument", "alternative explanation", "against this", "contrary"]):
        return passed("Hypothesis outputs must include counterarguments or alternatives.", ["Counterargument language was found."])
    return failed("Hypothesis outputs must include counterarguments or alternatives.", ["No counterargument or alternative-explanation signal found."])


def experiment_plan_present(agent: AgentContract, run: dict[str, Any]) -> EvalOutcome:
    output = _final_output(run)
    if isinstance(output, dict):
        for key in ["experiment_plan", "validation_plan", "measurement_plan", "rubric"]:
            if _non_empty(output.get(key)):
                return passed("Hypothesis outputs must include an experiment or validation plan.", [f"{key} is present."])
    if _contains_any(_as_text(output), ["experiment", "validation plan", "measurement", "metric", "test plan"]):
        return passed("Hypothesis outputs must include an experiment or validation plan.", ["Experiment or validation language was found."])
    return failed("Hypothesis outputs must include an experiment or validation plan.", ["No experiment, validation, measurement, or metric signal found."])


def unknown_evaluation(eval_name: str) -> EvaluationValidator:
    def _validator(agent: AgentContract, run: dict[str, Any]) -> EvalOutcome:
        return failed(
            "Every configured evaluation must have a registered validator.",
            [f"No evaluator is registered for {eval_name!r}."],
        )

    return _validator


VALIDATORS: dict[str, EvaluationValidator] = {
    "no_empty_answer": no_empty_answer,
    "output_schema_valid": output_schema_valid,
    "tool_policy_respected": tool_policy_respected,
    "approval_rules_respected": approval_rules_respected,
    "evidence_required": evidence_required,
    "claims_have_evidence": claims_have_evidence,
    "limitations_present": limitations_present,
    "false_positive_analysis_present": false_positive_analysis_present,
    "sigma_yaml_valid": sigma_yaml_valid,
    "yara_rule_valid": yara_rule_valid,
    "mitre_mapping_present": mitre_mapping_present,
    "counterarguments_present": counterarguments_present,
    "experiment_plan_present": experiment_plan_present,
}


def _final_output(run: dict[str, Any]) -> Any:
    return run.get("final_output")


def _tool_calls(run: dict[str, Any]) -> list[dict[str, Any]]:
    return list(run.get("tool_calls") or [])


def _evidence_items(run: dict[str, Any]) -> list[Any]:
    output = _final_output(run)
    if not isinstance(output, dict):
        return []
    evidence = output.get("evidence")
    if isinstance(evidence, list):
        return [item for item in evidence if _non_empty(item)]
    if _non_empty(evidence):
        return [evidence]
    return []


def _run_context(run: dict[str, Any]) -> str:
    status = run.get("status", "unknown")
    error_message = run.get("error_message")
    if error_message:
        return f"Run status is {status}: {error_message}"
    return f"Run status is {status}."


def _looks_like_tool_policy_error(error_message: str) -> bool:
    lowered = error_message.lower()
    return any(fragment in lowered for fragment in ["forbidden", "not allowlisted", "not allowed for domain", "tool policy"])


def _contains_any(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(needle in lowered for needle in needles)


def _non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(f"{key} {_as_text(item)}" for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_as_text(item) for item in value)
    return str(value)
