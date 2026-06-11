# Domain Stack

A domain stack is the packaging unit for domain-specific NeuroAgent behavior. It groups domain
metadata, agent contracts, tool boundaries, memory scope, risk policy, prompts, evaluations, and
future examples or benchmarks under one domain identity.

The runtime core is domain-agnostic. A domain stack is how the framework learns what a domain can
do without hard-coding domain behavior into the runtime.

## Location

Domain stacks live under:

```text
app/domains/{domain_id}/
```

The required root contract is:

```text
app/domains/{domain_id}/domain.yaml
```

Agent contracts live under:

```text
app/domains/{domain_id}/agents/*.yaml
```

Current examples:

```text
app/domains/research/domain.yaml
app/domains/cybersecurity/domain.yaml
app/domains/productivity/domain.yaml
app/domains/investor_gtm/domain.yaml
```

## Current Directory Shape

```text
app/domains/
  cybersecurity/
    domain.yaml
    agents/
      detection_critic.yaml
      sigma_rule_agent.yaml
      threat_researcher.yaml
      yara_rule_agent.yaml
  research/
    domain.yaml
    agents/
      hypothesis_generator.yaml
      literature_researcher.yaml
      research_critic.yaml
  productivity/
    domain.yaml
  investor_gtm/
    domain.yaml
```

Future domain stacks may add:

```text
prompts/
evals/
examples/
benchmarks/
policies/
workflows/
```

Those folders are domain-stack assets, but the current registry only loads `domain.yaml` and
`agents/*.yaml` directly.

## Registry Loading

The `DomainRegistry` loads domain stacks from `app/domains`:

```text
DomainRegistry.from_default_path()
        |
        v
Scan app/domains/*/domain.yaml
        |
        v
Validate each file as DomainContract
        |
        v
Scan sibling agents/*.yaml
        |
        v
Validate each file as AgentContract
        |
        v
Expose list/get methods for domains and agents
```

API routes use the registry for:

- `GET /domains`
- `GET /domains/{domain_id}`
- `POST /domains/{domain_id}/reload`
- `GET /agents`
- `GET /agents/{agent_id}`
- `POST /agents/{agent_id}/run`
- AutoResearch target discovery

Current limitation: `POST /domains/{domain_id}/reload` returns the current registry contract. It is
a route-level reload response around the loaded registry path, not a full hot-reload mechanism that
rebuilds every dependency in a running process.

## Python Schema

The source schema is defined in `app/contracts/domain_contract.py`:

```python
class RiskPolicy(BaseModel):
    default_tool_risk: Literal["low", "medium", "high", "critical"] = "medium"
    require_approval_for: list[str] = Field(default_factory=list)

class DomainContract(BaseModel):
    domain_id: str
    name: str
    version: str
    status: Literal["experimental", "active", "deprecated"] = "experimental"
    supported_tasks: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    default_memory_scope: list[str] = Field(default_factory=lambda: ["tenant", "domain"])
    risk_policy: RiskPolicy = Field(default_factory=RiskPolicy)
```

## Field Reference

### `domain_id`

Required string. Stable identifier for the domain stack.

Examples:

```yaml
domain_id: research
domain_id: cybersecurity
domain_id: investor_gtm
```

Rules:

- Keep it stable once external clients, stored runs, documents, or tool policies refer to it.
- Prefer lowercase snake-case identifiers.
- Match `AgentContract.domain` for agents owned by this stack.
- Match tool contract `allowed_domains` entries when tools are domain-restricted.

### `name`

Required string. Human-readable domain stack name.

Example:

```yaml
name: Cybersecurity Domain Stack
```

This is display metadata. Do not use it as a stable API identifier.

### `version`

Required string. Domain stack version.

Example:

```yaml
version: 0.1.0
```

Recommended versioning:

- Patch version for documentation, wording, or non-behavioral metadata changes.
- Minor version for backward-compatible additions such as new optional tasks, agents, tools, or evals.
- Major version for breaking changes to task names, agent IDs, tool boundaries, memory behavior, or
  output contracts.

### `status`

Optional lifecycle state. Defaults to `experimental`.

Allowed values:

```text
experimental | active | deprecated
```

Use the values consistently:

- `experimental`: contract may change; not guaranteed stable for production callers.
- `active`: supported domain stack with stable IDs and compatibility expectations.
- `deprecated`: retained for backward compatibility but should not be used for new workflows.

The current runtime does not block deprecated stacks automatically. Status is a governance signal for
API consumers, docs, tests, and future policy.

### `supported_tasks`

Optional list of domain-level tasks.

Example:

```yaml
supported_tasks:
  - threat_research
  - sigma_rule_generation
  - yara_rule_generation
  - detection_critique
```

This field describes the capability surface of the domain. It is useful for discovery, use-case
catalogs, UI grouping, evaluation coverage, and roadmap planning.

Guidelines:

- Use stable snake-case task names.
- Keep tasks domain-level, not agent implementation details.
- Add tasks when a domain has at least one agent or workflow that can support them.
- Remove or rename tasks only with a version bump and migration note.

### `agents`

Optional list of agent IDs owned by the domain.

Example:

```yaml
agents:
  - cybersecurity.threat_researcher
  - cybersecurity.sigma_rule_agent
  - cybersecurity.yara_rule_agent
  - cybersecurity.detection_critic
```

Current behavior:

- The registry loads actual agents from `app/domains/{domain_id}/agents/*.yaml`.
- The `agents` list in `domain.yaml` documents the intended domain agent set.
- The current registry does not automatically fail if this list and the files drift.

Recommendation: keep `agents` synchronized with the actual YAML files and cover this with tests for
production domains.

### `tools`

Optional list of tool IDs that belong to the domain's intended tool surface.

Example:

```yaml
tools:
  - rag.search
  - mitre.lookup
  - sigma.validate_yaml
  - yara.validate_rule
  - obsidian.write_note
  - file.write_artifact
```

Tool enforcement is distributed:

- `DomainContract.tools` documents the domain-level expected tools.
- `AgentContract.allowed_tools` controls what an individual agent may request.
- `ToolContract.allowed_domains` controls which domains may use a tool.
- `ToolPolicy` blocks forbidden tools, non-allowlisted tools, and tools outside their allowed
  domains.

Current limitation: the runtime primarily enforces the agent/tool contract combination. The domain
`tools` list is a governance and discovery boundary and should be kept consistent with agent
contracts and `app/tools/tools.yaml`.

### `default_memory_scope`

Optional list. Defaults to:

```yaml
default_memory_scope:
  - tenant
  - domain
```

Example:

```yaml
default_memory_scope:
  - tenant
  - domain
  - project
```

This field describes how memory and knowledge records should normally be scoped for the domain.

Typical scope values:

- `tenant`: isolate records by tenant.
- `domain`: isolate records by domain.
- `project`: include a project or workspace boundary.
- `user`: include user-specific memory.

Current persistence and RAG routes already use tenant and domain filters. Obsidian note records and
future memory policies should use this field to choose default frontmatter, retrieval filters, and
write locations.

### `risk_policy`

Optional domain-level risk policy.

Example:

```yaml
risk_policy:
  default_tool_risk: medium
  require_approval_for:
    - production_deployment
    - external_communication
    - destructive_file_action
```

Fields:

- `default_tool_risk`: default risk posture for tools or actions in this domain.
- `require_approval_for`: action categories that should require human approval.

Current behavior:

- Tool-level approval is enforced by `ToolContract.requires_approval` and high/critical tool risk.
- Agent-level approval expectations are captured by `AgentContract.human_approval_required_for`.
- Domain `risk_policy` is a governance contract and future policy input.

Use it to make domain risk explicit even before every category has a dedicated policy engine rule.

## Complete Example

```yaml
domain_id: cybersecurity
name: Cybersecurity Domain Stack
version: 0.1.0
status: experimental
supported_tasks:
  - threat_research
  - sigma_rule_generation
  - yara_rule_generation
  - detection_critique
agents:
  - cybersecurity.threat_researcher
  - cybersecurity.sigma_rule_agent
  - cybersecurity.yara_rule_agent
  - cybersecurity.detection_critic
tools:
  - rag.search
  - mitre.lookup
  - sigma.validate_yaml
  - yara.validate_rule
  - obsidian.write_note
  - file.write_artifact
default_memory_scope:
  - tenant
  - domain
  - project
risk_policy:
  default_tool_risk: medium
  require_approval_for:
    - production_deployment
    - external_communication
    - destructive_file_action
```

## Minimal Example

```yaml
domain_id: productivity
name: Productivity Domain Stack
version: 0.1.0
status: experimental
supported_tasks:
  - focus_review
  - weekly_planning
agents: []
tools:
  - obsidian.write_note
default_memory_scope:
  - tenant
  - domain
risk_policy:
  default_tool_risk: medium
  require_approval_for:
    - external_communication
```

## Relationship to Agent Contracts

A domain stack declares which agents belong to the domain. Each agent contract then defines the
runtime behavior for one agent.

Consistency rules:

- `AgentContract.domain` should equal `DomainContract.domain_id`.
- `AgentContract.agent_id` should usually start with `{domain_id}.`.
- Domain `agents` should list the agent IDs present in `agents/*.yaml`.
- Agent output schemas and evaluations should support the domain's `supported_tasks`.
- Agent `allowed_tools` should be a subset of the domain's intended `tools` unless there is a clear
  exception.

The registry currently validates domain and agent files independently. Add tests when you need
strict cross-file consistency.

## Relationship to Tool Contracts

Tools are globally registered in `app/tools/tools.yaml`, but domain stacks define the expected tool
surface for a domain.

The effective tool boundary is:

```text
DomainContract.tools
AgentContract.allowed_tools
AgentContract.forbidden_tools
ToolContract.allowed_domains
ToolContract.requires_approval
ToolContract.risk_level
```

Example:

- `cybersecurity` can list `sigma.validate_yaml`.
- `sigma_rule_agent` can include `sigma.validate_yaml` in `allowed_tools`.
- The tool contract must allow the `cybersecurity` domain.
- If a tool is high risk or requires approval, execution stops for approval.

## Relationship to RAG

Domain stacks are part of the RAG isolation boundary.

Document and retrieval metadata include:

```text
tenant_id
domain_id
document_id
chunk_id
source_uri
hash
```

The domain stack influences:

- which agents can call `rag.search`,
- which domain ID is persisted on runs and documents,
- which domain filter is used during RAG search,
- which citations and chunks are relevant to a run.

For production RAG behavior, keep domain IDs stable. Renaming a domain affects persisted documents,
chunks, embedding records, Qdrant payload filters, and retrieval events.

## Relationship to Obsidian Memory

Domain stacks guide memory scoping for Obsidian notes and future memory records.

Recommended note frontmatter should include:

```yaml
tenant_id: default
domain_id: research
agent_id: research.literature_researcher
run_id: ...
```

`default_memory_scope` should be used by future memory writers to decide whether notes and records
are tenant-level, domain-level, project-level, or user-level.

## Relationship to Evaluations

Domain stacks define high-level capability areas. Agent contracts select specific evaluation
validators.

Recommended mapping:

- `literature_review`: `claims_have_evidence`, `limitations_present`
- `hypothesis_generation`: `counterarguments_present`, `experiment_plan_present`
- `sigma_rule_generation`: `sigma_yaml_valid`, `false_positive_analysis_present`
- `yara_rule_generation`: `yara_rule_valid`
- `threat_research`: `mitre_mapping_present`, `evidence_required`

Domain-level tasks should be represented by at least one agent evaluation path before the domain is
considered production-ready.

## Relationship to AutoResearcher

AutoResearcher treats domain stacks as measurable assets.

Default target discovery includes:

- `app/domains/{domain_id}/domain.yaml`
- `app/domains/{domain_id}/agents/*.yaml`
- shared prompt templates
- tool policy metadata
- eval validator assets

Use the improvement endpoint to validate domain contracts and generate a keep/discard package:

```bash
curl -X POST http://127.0.0.1:8011/autoresearch/domains/cybersecurity/improvement-run \
  -H "Content-Type: application/json" \
  -d '{"budget_minutes": 30, "primary_metric": "contract_validity", "targets": []}'
```

## API Surface

List domains:

```bash
curl http://127.0.0.1:8011/domains
```

Get one domain:

```bash
curl http://127.0.0.1:8011/domains/cybersecurity
```

Reload/read a domain:

```bash
curl -X POST http://127.0.0.1:8011/domains/cybersecurity/reload
```

List agents:

```bash
curl http://127.0.0.1:8011/agents
```

Run an agent:

```bash
curl -X POST http://127.0.0.1:8011/agents/research.literature_researcher/run \
  -H "Content-Type: application/json" \
  -d '{"input_payload": {"research_question": "What are the main risks of tool use?"}}'
```

If API key authentication is enabled, include the configured `X-API-Key` header.

## Adding a New Domain Stack

1. Create the directory:

```text
app/domains/{domain_id}/
```

2. Add `domain.yaml`.

3. Add one or more agent contracts under:

```text
app/domains/{domain_id}/agents/
```

4. Add or reuse tool contracts in `app/tools/tools.yaml`.

5. Ensure tool contracts include the new `domain_id` in `allowed_domains` when needed.

6. Add evaluation validators or reuse existing ones.

7. Add tests for registry loading, contract validation, tool policy, and at least one agent run.

8. Update docs, user scenarios, and roadmap entries if this domain is user-facing.

9. Run AutoResearcher contract validation for the domain.

10. Bump versions when changing existing public behavior.

## Design Checklist

Before marking a domain stack ready:

- `domain_id` is stable and matches directory naming.
- `status` correctly reflects maturity.
- `supported_tasks` are concrete and testable.
- `agents` lists intended agent IDs.
- Each listed agent has a matching YAML file or a tracked follow-up.
- Each agent's `domain` matches the domain ID.
- Domain `tools` matches the intended tool surface.
- Agent `allowed_tools` do not exceed the domain's intended tool boundary.
- High-risk tools require approval through tool contracts or agent policy.
- `default_memory_scope` matches tenant/domain/project isolation expectations.
- Domain-specific evaluations exist for the important tasks.
- RAG and Obsidian usage include domain IDs for isolation.
- Contract changes have tests and version updates.

## Common Mistakes

- Renaming `domain_id` after runs, documents, chunks, or vectors already use it.
- Adding an agent YAML file but forgetting to list it in `domain.yaml`.
- Listing a tool in `domain.yaml` while the tool contract does not allow the domain.
- Assuming `risk_policy` alone enforces approvals.
- Letting agent `allowed_tools` drift beyond the domain's intended tools.
- Treating `reload` as a full process-wide hot reload.
- Adding supported tasks without evaluation coverage.
- Using one broad domain for unrelated workflows instead of separate domain stacks.

## Persistence Impact

Domain IDs are persisted in:

- agent runs,
- run steps and tool traces through run relationships,
- documents and chunks,
- embedding records through Qdrant payloads,
- retrieval events,
- evaluation records,
- approval and audit records,
- Obsidian note records.

For production systems, a domain rename is a data migration, not a simple YAML edit.

## Change Management

Recommended process for domain-stack changes:

1. Update `domain.yaml`.
2. Update agent contracts and tool contracts together.
3. Run contract tests.
4. Run runtime and tool policy tests.
5. Run RAG or Obsidian tests if the domain uses those layers.
6. Generate an AutoResearch improvement package.
7. Update API docs or user scenarios if the public behavior changed.

Useful checks:

```bash
pytest tests/test_agent_contracts.py
pytest tests/test_tool_policy.py
pytest tests/test_runtime.py tests/test_model_gateway_runtime.py
pytest tests/test_autoresearcher_pipeline.py
```
