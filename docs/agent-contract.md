# Agent Contract

Agent contracts are YAML-backed runtime contracts validated by `AgentContract`. They define what an
agent is allowed to do, what input it accepts, what output it must return, which tools it may use,
which actions require human approval, and which evaluations should be applied after a run.

The contract is intentionally explicit. NeuroAgent should not rely on hidden prompt conventions to
determine agent behavior, safety boundaries, or output shape.

## Location

Agent contracts live under a domain stack:

```text
app/domains/{domain_id}/agents/{agent_name}.yaml
```

Examples:

```text
app/domains/research/agents/literature_researcher.yaml
app/domains/cybersecurity/agents/sigma_rule_agent.yaml
```

The domain registry loads agents from these files when the API starts or when a domain stack is
reloaded. An agent contract is not standalone: its `domain` must refer to a loaded domain contract,
and its tools should be consistent with the domain's allowed tool surface.

## Runtime Role

The agent contract participates in the full run lifecycle:

```text
POST /agents/{agent_id}/run
        |
        v
Load AgentContract from DomainRegistry
        |
        v
Validate request payload against input_schema
        |
        v
Create execution plan from role, goal, tools, and schemas
        |
        v
Execute governed tools through ToolPolicy
        |
        v
Call the configured model gateway
        |
        v
Validate final output against output_schema
        |
        v
Persist run trace, artifacts, tool calls, and evaluations
```

This means contract changes affect API behavior, model prompts, allowed tool execution, persisted
run traces, and evaluation results.

## Python Schema

The source schema is defined in `app/contracts/agent_contract.py`:

```python
RiskLevel = Literal["low", "medium", "high", "critical"]

class JsonSchema(BaseModel):
    type: str = "object"
    required: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)

class AgentContract(BaseModel):
    agent_id: str
    name: str
    version: str
    domain: str
    risk_level: RiskLevel = "low"
    role: str
    goal: str
    input_schema: JsonSchema
    output_schema: JsonSchema
    allowed_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    human_approval_required_for: list[str] = Field(default_factory=list)
    evaluation: list[str] = Field(default_factory=list)
```

## Field Reference

### `agent_id`

Required string. Globally identifies the agent.

Recommended format:

```text
{domain_id}.{agent_name}
```

Examples:

```yaml
agent_id: research.literature_researcher
agent_id: cybersecurity.sigma_rule_agent
```

Rules:

- Keep it stable once external callers depend on it.
- Avoid spaces and display-only names.
- Prefer lowercase domain and snake-case agent names.
- The API uses this value in `/agents/{agent_id}` and `/agents/{agent_id}/run`.

### `name`

Required string. Human-readable display name.

Example:

```yaml
name: Sigma Rule Agent
```

This field is safe to change for display purposes, but it should not be used as a stable identifier.

### `version`

Required string. Contract version.

Example:

```yaml
version: 0.1.0
```

Use semantic versioning when possible:

- Patch version for wording-only prompt/goal changes that preserve schemas.
- Minor version for backward-compatible schema or evaluation additions.
- Major version for breaking input/output schema changes.

### `domain`

Required string. The domain stack that owns the agent.

Example:

```yaml
domain: cybersecurity
```

The value should match the domain contract's `domain_id`. Tool policy also uses this value when
checking whether a tool's `allowed_domains` includes the agent's domain.

### `risk_level`

Optional risk classification. Defaults to `low`.

Allowed values:

```text
low | medium | high | critical
```

Use this as the agent-level risk signal:

- `low`: read-only or deterministic internal behavior.
- `medium`: external reads, file writes to controlled artifact locations, or domain-sensitive
  synthesis.
- `high`: potentially destructive, externally visible, or security-sensitive actions.
- `critical`: actions that can affect production systems, regulated workflows, credentials, or
  irreversible external state.

The current tool approval gate is driven primarily by tool contracts and tool policy, but agent risk
still matters for review, governance, evaluation, and future policy expansion.

### `role`

Required string. Describes the persona and operating boundary of the agent.

Example:

```yaml
role: >
  You are a detection engineering agent specialized in Sigma rules and telemetry.
```

Guidelines:

- Keep it domain-specific.
- State the agent's expertise and constraints.
- Do not place output schema details only in `role`; those belong in `output_schema`.
- Do not use `role` to grant access to tools. Tool access must be declared in `allowed_tools`.

### `goal`

Required string. Defines the outcome the agent should optimize for.

Example:

```yaml
goal: >
  Convert threat behavior descriptions into explainable Sigma detection logic with evidence.
```

Good goals are measurable and aligned with evaluation rules. If an output requires evidence,
confidence, limitations, or false-positive analysis, make that visible in both `goal` and
`output_schema`.

### `input_schema`

Required object. Defines the accepted request payload for `/agents/{agent_id}/run`.

Example:

```yaml
input_schema:
  type: object
  required: [threat_description, target_platform]
  properties:
    threat_description:
      type: string
    target_platform:
      type: string
    log_sources:
      type: array
      items:
        type: string
```

Current validation behavior:

- `type` must be `object`.
- Fields listed in `required` must exist in the payload.
- Fields declared in `properties` are checked against simple JSON types.
- Supported simple types are `string`, `number`, `integer`, `boolean`, `object`, and `array`.
- Boolean values are rejected for `number` and `integer`.
- Additional payload fields are currently allowed.
- Nested schema constraints such as `items`, `enum`, `minimum`, `format`, `oneOf`, and deep object
  validation are descriptive today unless a future validator expands support.

Important runtime behavior:

- The API injects or validates `tenant_id` through API key auth before runtime execution.
- The runtime validates `input_payload` before planning and model execution.
- Invalid input fails fast with a contract validation error.

### `output_schema`

Required object. Defines the final model output shape.

Example:

```yaml
output_schema:
  type: object
  required: [summary, sigma_rule, evidence, false_positive_analysis, confidence_score]
  properties:
    summary:
      type: string
    sigma_rule:
      type: object
    evidence:
      type: array
    false_positive_analysis:
      type: string
    confidence_score:
      type: number
    open_questions:
      type: array
```

Runtime behavior:

- The model gateway must return a JSON object.
- The runtime validates the final output against `output_schema`.
- If output validation fails, the run is marked `failed`, `final_output` is cleared, and the error
  is persisted.
- The evaluation runner also applies `output_schema_valid` by default.

Design rules:

- Include every field that callers need in `required`.
- Keep optional fields in `properties` so model providers see the expected shape.
- Prefer structured arrays/objects over free-text blobs for evidence, citations, rules, actions, or
  decisions.
- Keep schema names stable because downstream tools, evals, and UIs may depend on them.

### `allowed_tools`

Optional list of tool IDs. If non-empty, the agent can only call tools in this list.

Example:

```yaml
allowed_tools:
  - rag.search
  - sigma.validate_yaml
  - mitre.lookup
  - obsidian.write_note
  - file.write_artifact
```

Tool policy applies three checks:

1. The tool must not appear in `forbidden_tools`.
2. If `allowed_tools` is non-empty, the tool must appear in `allowed_tools`.
3. If the tool contract has `allowed_domains`, the agent's `domain` must be included.

Recommendation: always use an explicit `allowed_tools` list for production agents.

### `forbidden_tools`

Optional list of tool IDs that are blocked for this agent.

Example:

```yaml
forbidden_tools:
  - shell.execute
  - production.deploy_rule
```

`forbidden_tools` wins over `allowed_tools`. Use it for high-risk capabilities that should remain
blocked even if a broad allowlist is introduced later.

### `human_approval_required_for`

Optional list of tool IDs or action IDs that require human approval for this agent.

Example:

```yaml
human_approval_required_for:
  - production.deploy_rule
  - external_email.send
```

Current behavior:

- Tool contracts with `requires_approval: true` or `risk_level: high|critical` create approval
  gates.
- The evaluation runner checks agent-level approval expectations through
  `approval_rules_respected`.
- This field is also useful for future policy engines where agent-specific approval rules may be
  enforced before execution.

Use this field to document agent-specific approval boundaries even when the tool contract already
requires approval.

### `evaluation`

Optional list of registered evaluation validator names.

Example:

```yaml
evaluation:
  - output_schema_valid
  - evidence_required
  - sigma_yaml_valid
  - false_positive_analysis_present
```

The evaluation runner always applies the default evaluations first:

```text
no_empty_answer
output_schema_valid
tool_policy_respected
approval_rules_respected
```

Then it applies the agent-specific validators listed in `evaluation`, preserving order and removing
duplicates.

Registered validators currently include:

```text
no_empty_answer
output_schema_valid
tool_policy_respected
approval_rules_respected
evidence_required
claims_have_evidence
limitations_present
false_positive_analysis_present
sigma_yaml_valid
yara_rule_valid
mitre_mapping_present
counterarguments_present
experiment_plan_present
```

Unknown evaluation names do not silently pass. They produce a failed evaluation result so missing
validator implementations are visible.

## Complete Example

```yaml
agent_id: cybersecurity.sigma_rule_agent
name: Sigma Rule Agent
version: 0.1.0
domain: cybersecurity
risk_level: medium
role: >
  You are a detection engineering agent specialized in Sigma rules and telemetry.
goal: >
  Convert threat behavior descriptions into explainable Sigma detection logic with evidence.
input_schema:
  type: object
  required: [threat_description, target_platform]
  properties:
    threat_description:
      type: string
    target_platform:
      type: string
    log_sources:
      type: array
      items:
        type: string
output_schema:
  type: object
  required: [summary, sigma_rule, evidence, false_positive_analysis, confidence_score]
  properties:
    summary:
      type: string
    sigma_rule:
      type: object
    evidence:
      type: array
    false_positive_analysis:
      type: string
    confidence_score:
      type: number
    open_questions:
      type: array
allowed_tools:
  - rag.search
  - sigma.validate_yaml
  - mitre.lookup
  - obsidian.write_note
  - file.write_artifact
forbidden_tools:
  - shell.execute
  - production.deploy_rule
human_approval_required_for:
  - production.deploy_rule
  - external_email.send
evaluation:
  - output_schema_valid
  - evidence_required
  - sigma_yaml_valid
  - false_positive_analysis_present
```

## Minimal Example

```yaml
agent_id: research.summary_agent
name: Summary Agent
version: 0.1.0
domain: research
risk_level: low
role: >
  You summarize research questions with clear limitations.
goal: >
  Return a concise, evidence-aware summary.
input_schema:
  type: object
  required: [research_question]
  properties:
    research_question:
      type: string
output_schema:
  type: object
  required: [summary]
  properties:
    summary:
      type: string
allowed_tools:
  - rag.search
forbidden_tools:
  - shell.execute
human_approval_required_for: []
evaluation:
  - limitations_present
```

## Contract Design Checklist

Before adding or changing an agent contract, verify:

- `agent_id` is stable and follows `{domain}.{agent}` naming.
- `domain` matches an existing domain contract.
- `version` reflects the compatibility impact of the change.
- `role` and `goal` are domain-specific and measurable.
- `input_schema.required` includes all fields needed for a meaningful run.
- `output_schema.required` includes all fields external callers and evals depend on.
- `allowed_tools` is explicit for production agents.
- `forbidden_tools` includes known dangerous tools such as `shell.execute` unless the agent truly
  needs them.
- Approval-sensitive tools are listed in `human_approval_required_for`.
- `evaluation` includes validators that match the promised output.
- Contract changes are covered by tests or an AutoResearch improvement run.

## Tool Policy Interaction

Tool access is decided by the combination of agent contract and tool contract:

```text
AgentContract.allowed_tools
AgentContract.forbidden_tools
AgentContract.domain
ToolContract.allowed_domains
ToolContract.risk_level
ToolContract.requires_approval
```

Examples:

- If `shell.execute` appears in `forbidden_tools`, the agent cannot use it even if a plan asks for
  it.
- If `allowed_tools` is non-empty and `web.search` is not listed, `web.search` is blocked.
- If `rag.search` is allowed only for `research` and `cybersecurity`, an agent in another domain
  cannot use it.
- If `file.delete_file` has `requires_approval: true`, the tool call must stop for approval instead
  of executing directly.

## Evaluation Interaction

Evaluations make the contract measurable. For example:

- An agent requiring `evidence` in `output_schema` should usually include `evidence_required` or
  `claims_have_evidence`.
- A research agent should usually include `limitations_present`.
- A Sigma agent should include `sigma_yaml_valid` and `false_positive_analysis_present`.
- A YARA agent should include `yara_rule_valid`.
- A hypothesis agent should include `counterarguments_present` and `experiment_plan_present`.

The goal is to make failures visible as evaluation records rather than hidden quality regressions.

## Persistence Impact

Agent contract fields are copied into runtime behavior and persisted traces:

- `agent_id` and `domain` are saved on every run.
- `input_schema` and `output_schema` determine validation success or failure.
- `allowed_tools`, `forbidden_tools`, and approval requirements influence tool call records.
- `evaluation` determines which evaluation results are persisted after a run.

Future Postgres-backed contract seeding can snapshot agent definitions into the database for audit
and version history.

## AutoResearch Impact

Agent contracts are measurable assets for AutoResearcher. The default AutoResearch target discovery
includes each domain's agent YAML files. An improvement run can snapshot agent contracts, validate
them through `AgentContract`, and include them in the keep/discard package.

Use this when changing agent contracts:

```bash
curl -X POST http://127.0.0.1:8011/autoresearch/domains/cybersecurity/improvement-run \
  -H "Content-Type: application/json" \
  -d '{"budget_minutes": 30, "primary_metric": "contract_validity", "targets": []}'
```

## Common Mistakes

- Putting required output behavior only in `role` or `goal` instead of `output_schema`.
- Allowing broad tools without an explicit `forbidden_tools` list.
- Adding an evaluation name without implementing a registered validator.
- Changing output field names without updating evals, tests, clients, and prompt templates.
- Treating the current schema validator as a full JSON Schema implementation.
- Forgetting that tool contracts also restrict domain access.
- Using `risk_level: low` for agents that write files, create external records, or handle sensitive
  domain actions.

## Change Management

Recommended process for contract changes:

1. Update the YAML contract.
2. Run contract and runtime tests.
3. Run any domain-specific eval tests.
4. Generate an AutoResearch improvement package for contract validity and target coverage.
5. Review API clients or UI code that depends on input/output fields.
6. Bump `version` according to compatibility impact.

Useful checks:

```bash
pytest tests/test_agent_contracts.py
pytest tests/test_runtime.py tests/test_model_gateway_runtime.py
pytest tests/test_autoresearcher_pipeline.py
```
