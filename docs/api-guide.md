# NeuroAgent Framework API Guide

Version: `0.1.0`

Base URL for local development:

```text
http://127.0.0.1:8011
```

Machine-readable OpenAPI specification:

```text
docs/openapi.json
```

## Current API Status

The current API is a v0.1 backend foundation. It supports contract discovery, agent runs, trace retrieval, tool registry inspection, approval state transitions, document ingestion, repository-backed RAG metadata, lexical RAG fallback, Obsidian note payloads or vault writes, evaluation lookup, storage status, and model provider status.

The runtime defaults to a stub model gateway and an in-memory repository for development and tests. PostgreSQL persistence and provider-backed model gateways are available through environment configuration.

## Core Concepts

### Domain Stack

A domain stack defines a package of agents, tools, policies, memory scope, and supported tasks. Domain stack contracts are loaded from `app/domains/*/domain.yaml`.

Examples:

- `research`
- `cybersecurity`
- `productivity`
- `investor_gtm`

### Agent Contract

An agent is defined by a YAML contract. The runtime validates agent input against the contract input schema, routes execution through the planner and model gateway, validates final output against the output schema, and persists trace records.

### Agent Run

An agent run is the main execution object. A run includes:

- input payload
- resolved plan
- final output or error
- token usage
- cost estimate
- model name
- steps
- tool calls
- artifacts
- evaluations

Trace records are stored as first-class repository records, then rehydrated into the run response.

### Tool Governance

Tools are defined by contracts under `app/tools/tools.yaml`. The runtime enforces:

- allowed tools
- forbidden tools
- domain allowlists
- risk levels
- approval requirements

High-risk tools create pending approval requests instead of executing directly.
Every tool contract must have an explicit registry handler. Unknown tools and missing handlers are
not allowed to fall back to a generic echo implementation. The direct tool test endpoint is a
development surface; high-risk `shell.execute` still returns an approval-required response and does
not execute shell commands through the registry.

File tools are constrained by `FILE_TOOL_ROOT`. `file.read_file`, `file.write_file`,
`file.update_file`, and `file.delete_file` reject paths that resolve outside that root.
`file.delete_file` is high risk and requires approval when invoked through governed agent execution.

GitHub tools use the GitHub REST API through `GITHUB_TOKEN`. Read-only tools can inspect
repositories, issues, and file contents. Write tools such as `github.create_issue`,
`github.create_issue_comment`, and `github.update_file` are approval-required in governed agent
execution. Use a fine-grained personal access token with the minimum repository permissions needed
for the enabled operations.

RAG tools include `rag.ingest_document`, `rag.index_document`, `rag.search`, and
`rag.delete_document_vectors`. Search uses vector retrieval when configured and falls back to
repository lexical matching when vector search is unavailable. Vector deletion is approval-required.

## Error Model

The API currently uses standard FastAPI JSON errors:

```json
{
  "detail": "Run not found"
}
```

Common status codes:

- `200`: successful request
- `400`: runtime or contract validation failure
- `404`: requested domain, agent, tool, run, or approval was not found
- `422`: FastAPI request validation failure

## Health

### GET `/health`

Returns service status.

Example:

```bash
curl http://127.0.0.1:8011/health
```

Response:

```json
{
  "status": "ok",
  "app": "neuroagent-framework",
  "environment": "development"
}
```

## Domains

### GET `/domains`

Lists loaded domain stack contracts.

```bash
curl http://127.0.0.1:8011/domains
```

### GET `/domains/{domain_id}`

Returns one domain stack contract.

```bash
curl http://127.0.0.1:8011/domains/cybersecurity
```

### POST `/domains/{domain_id}/reload`

Reloads a domain contract. In v0.1 this is a stubbed reload response around the current registry read path.

```bash
curl -X POST http://127.0.0.1:8011/domains/cybersecurity/reload
```

## Agents

### GET `/agents`

Lists loaded agent contracts.

```bash
curl http://127.0.0.1:8011/agents
```

### GET `/agents/{agent_id}`

Returns one agent contract.

```bash
curl http://127.0.0.1:8011/agents/research.literature_researcher
```

### POST `/agents/{agent_id}/run`

Creates and executes an agent run.

Request body:

```json
{
  "input_payload": {}
}
```

Research example:

```bash
curl -X POST http://127.0.0.1:8011/agents/research.literature_researcher/run \
  -H "Content-Type: application/json" \
  -d '{
    "input_payload": {
      "research_question": "Sigma rules as behavioral vectors for threat detection"
    }
  }'
```

Cybersecurity Sigma example:

```bash
curl -X POST http://127.0.0.1:8011/agents/cybersecurity.sigma_rule_agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "input_payload": {
      "threat_description": "Suspicious PowerShell execution with encoded command",
      "target_platform": "windows",
      "log_sources": ["process_creation"]
    }
  }'
```

Successful response shape:

```json
{
  "id": "run-id",
  "tenant_id": "default",
  "user_id": "anonymous",
  "domain_id": "research",
  "agent_id": "research.literature_researcher",
  "status": "completed",
  "input_payload": {},
  "resolved_plan": {},
  "final_output": {},
  "error_message": null,
  "token_usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0
  },
  "cost_estimate": 0.0,
  "model": "stub-model",
  "steps": [],
  "tool_calls": [],
  "artifacts": [],
  "evaluations": []
}
```

If input or output contract validation fails, the route returns `400`.

## Runs

### GET `/runs`

Lists stored runs.

```bash
curl http://127.0.0.1:8011/runs
```

### GET `/runs/{run_id}`

Returns a rehydrated run with steps, tool calls, artifacts, and evaluations.

```bash
curl http://127.0.0.1:8011/runs/{run_id}
```

### GET `/runs/{run_id}/steps`

Returns step trace records for a run.

### GET `/runs/{run_id}/tool-calls`

Returns tool call trace records for a run.

### GET `/runs/{run_id}/artifacts`

Returns artifacts for a run, including `run_trace.json`.

### POST `/runs/{run_id}/cancel`

Marks a run as cancelled without deleting trace records.

```bash
curl -X POST http://127.0.0.1:8011/runs/{run_id}/cancel
```

## Approvals

### GET `/approvals/pending`

Lists pending human approval requests.

```bash
curl http://127.0.0.1:8011/approvals/pending
```

### POST `/approvals/{approval_id}/approve`

Marks an approval request as approved.

```bash
curl -X POST http://127.0.0.1:8011/approvals/{approval_id}/approve
```

### POST `/approvals/{approval_id}/reject`

Marks an approval request as rejected.

```bash
curl -X POST http://127.0.0.1:8011/approvals/{approval_id}/reject
```

## Use Cases

The use case catalog is a built-in manual test harness. It exposes ready-made scenarios with payloads, expected results, and follow-up endpoints.

### GET `/use-cases`

Lists built-in user test scenarios.

```bash
curl http://127.0.0.1:8011/use-cases
```

### GET `/use-cases/{use_case_id}`

Returns one use case definition.

```bash
curl http://127.0.0.1:8011/use-cases/research-agent-run
```

### POST `/use-cases/{use_case_id}/run`

Runs one built-in use case.

```bash
curl -X POST http://127.0.0.1:8011/use-cases/cybersecurity-sigma-run/run
```

Available IDs:

- `research-agent-run`
- `cybersecurity-sigma-run`
- `rag-ingest-search`
- `autoresearch-domain-plan`
- `obsidian-note-stub`

## Autoresearch

Autoresearch adapts Karpathy-style fixed-budget improvement loops for NeuroAgent domain assets. It generates `program.md`, an experiment plan, a measurement rubric, and an improvement backlog for measurable assets such as agent contracts, prompt templates, domain contracts, tool policies, and eval rubrics. It can also build an improvement-run package with asset snapshots, validation measurements, metric comparison, and a keep/discard decision.

### GET `/autoresearch/domains/{domain_id}/targets`

Returns the default measurable improvement targets for a domain.

```bash
curl http://127.0.0.1:8011/autoresearch/domains/cybersecurity/targets
```

### POST `/autoresearch/domains/{domain_id}/plan`

Generates a fixed-budget domain improvement plan.

Request:

```json
{
  "budget_minutes": 30,
  "primary_metric": "eval_pass_rate",
  "targets": []
}
```

Custom target example:

```bash
curl -X POST http://127.0.0.1:8011/autoresearch/domains/cybersecurity/plan \
  -H "Content-Type: application/json" \
  -d '{
    "budget_minutes": 20,
    "primary_metric": "contract_validity",
    "targets": [
      {
        "asset_type": "agent_contract",
        "asset_id": "cybersecurity.sigma_rule_agent",
        "path": "app/domains/cybersecurity/agents/sigma_rule_agent.yaml",
        "objective": "Improve measurable Sigma output contract quality.",
        "measurements": []
      }
    ]
  }'
```

Response includes:

- `program_markdown`
- `artifacts.program.md`
- `artifacts.experiment_plan.json`
- `artifacts.measurement_rubric.json`
- `artifacts.improvement_backlog.md`

### POST `/autoresearch/domains/{domain_id}/improvement-run`

Builds a measurable improvement package for the domain. The request body is the same as the plan
endpoint. If `targets` is empty, the framework discovers the default asset boundary for the domain.

```bash
curl -X POST http://127.0.0.1:8011/autoresearch/domains/cybersecurity/improvement-run \
  -H "Content-Type: application/json" \
  -d '{
    "budget_minutes": 30,
    "primary_metric": "contract_validity",
    "targets": []
  }'
```

Response includes:

- `run_id`
- `plan`
- `asset_snapshots`
- `measurement_results`
- `keep_decision`
- `artifacts.asset_snapshots.json`
- `artifacts.measurement_results.json`
- `artifacts.metric_comparison.json`
- `artifacts.keep_discard_decision.json`

The endpoint does not apply patches. It returns a reviewable package that can be persisted as
artifacts or used by a future worker-backed experiment runner.

## Documents and RAG

### POST `/documents/ingest`

Ingests a text document into the in-memory RAG layer.

Request:

```json
{
  "title": "Sigma Notes",
  "content": "Sigma rules can represent behavioral threat vectors.",
  "metadata": {
    "source_type": "local",
    "domain_id": "cybersecurity"
  }
}
```

Example:

```bash
curl -X POST http://127.0.0.1:8011/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sigma Notes",
    "content": "Sigma rules can represent behavioral threat vectors.",
    "metadata": {
      "source_type": "local",
      "domain_id": "cybersecurity"
    }
  }'
```

### POST `/documents/upload`

Alias for the current ingest behavior. In v0.1 it accepts the same JSON body as `/documents/ingest`.

### GET `/documents`

Lists ingested documents.

### GET `/documents/{document_id}`

Returns one ingested document.

### POST `/rag/search`

Searches repository-backed chunks and returns cited evidence records. When Qdrant is configured,
the API embeds the query, searches the vector collection with tenant/domain filters, hydrates chunk
metadata from the repository, and falls back to lexical repository search when vector results are
unavailable.

Request:

```json
{
  "query": "behavioral threat",
  "tenant_id": "default",
  "domain_id": "research",
  "limit": 5
}
```

Response item shape:

```json
{
  "status": "searched",
  "mode": "vector",
  "query": "behavioral threat",
  "results": [
    {
      "chunk_id": "document-id_chunk_0",
      "source_metadata": {},
      "score": 0.91,
      "citation_id": "cite:document-id_chunk_0",
      "confidence": 0.641,
      "text": "chunk text"
    }
  ]
}
```

## Tools

### GET `/tools`

Lists registered tool contracts.

### GET `/tools/{tool_id}`

Returns one tool contract.

### POST `/tools/{tool_id}/test`

Runs a registered tool handler directly with test input. This is intended for development only.
When a token is configured, direct tests for external write tools can affect external systems; use
governed agent execution for approval-gated operations.

Request:

```json
{
  "input_payload": {
    "value": 42
  }
}
```

Example:

```bash
curl -X POST http://127.0.0.1:8011/tools/local.echo/test \
  -H "Content-Type: application/json" \
  -d '{"input_payload": {"value": 42}}'
```

## Obsidian

### POST `/obsidian/notes`

Creates an Obsidian note response with Markdown frontmatter. With `OBSIDIAN_ENABLED=false`, the
response is deterministic and does not write to disk. With `OBSIDIAN_ENABLED=true`, the note is
written to `OBSIDIAN_VAULT_PATH`.

Request:

```json
{
  "title": "Agent Run Note",
  "body": "Body text",
  "folder": "00_Inbox"
}
```

### GET `/obsidian/notes/search?query={query}`

Searches the configured Obsidian vault when `OBSIDIAN_ENABLED=true`; otherwise returns a deterministic
disabled-mode response.

### POST `/obsidian/agent-run-note`

Writes an agent-run style note response under `03_Agent_Runs/Daily`.

## Evaluations

### POST `/evals/run/{run_id}`

Returns the evaluation records associated with a run. In v0.1 the evaluations are generated during runtime execution.

### GET `/evals/{run_id}`

Returns evaluation records for a run.

### GET `/evals/reports`

Returns an evaluation report summary across persisted runs, including pass/fail counts, pass rate,
average score, and failed-evaluation counts.

## End-to-End Development Flow

1. Check health.
2. List domains.
3. List agents.
4. Run an agent.
5. Fetch run details.
6. Inspect steps, tool calls, artifacts, and evals.

Example:

```bash
curl http://127.0.0.1:8011/health
curl http://127.0.0.1:8011/domains
curl http://127.0.0.1:8011/agents

curl -X POST http://127.0.0.1:8011/agents/research.literature_researcher/run \
  -H "Content-Type: application/json" \
  -d '{"input_payload": {"research_question": "Agentic research governance"}}'
```

Copy the returned `id`, then:

```bash
curl http://127.0.0.1:8011/runs/{run_id}
curl http://127.0.0.1:8011/runs/{run_id}/steps
curl http://127.0.0.1:8011/runs/{run_id}/tool-calls
curl http://127.0.0.1:8011/runs/{run_id}/artifacts
curl http://127.0.0.1:8011/evals/{run_id}
```

## v0.1 Limitations

- API key authentication can be enabled with `API_AUTH_ENABLED=true`; clients then send `X-API-Key`.
- Tenant isolation is represented in payloads but not enforced by middleware.
- Runtime persistence defaults to in-memory storage for local development and tests; Postgres can be selected with `REPOSITORY_BACKEND=postgres`.
- The model gateway defaults to `stub`, but OpenAI/ChatGPT API, OpenRouter, Claude, Gemini, and Ollama adapters are available through environment configuration.
- RAG search currently uses lexical matching over repository-backed chunks; Qdrant vector retrieval is implemented as an adapter but is not yet the end-to-end API search path.
- Obsidian disabled mode returns deterministic note payloads; enabled mode writes/searches the mounted vault directly.
- Tool testing endpoint is development-only and should not be exposed as-is in production.
