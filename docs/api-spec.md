# NeuroAgent Framework API Specification

Version: `0.1.0`

Canonical machine-readable spec:

```text
docs/openapi.json
```

Local server:

```text
http://127.0.0.1:8011
```

## Endpoint Index

| Method | Path | Tag | Purpose |
|---|---|---|---|
| GET | `/health` | health | Check API health and environment. |
| GET | `/domains` | domains | List loaded domain stack contracts. |
| GET | `/domains/{domain_id}` | domains | Get one domain stack contract. |
| POST | `/domains/{domain_id}/reload` | domains | Reload/read a domain stack contract. |
| GET | `/agents` | agents | List loaded agent contracts. |
| GET | `/agents/{agent_id}` | agents | Get one agent contract. |
| POST | `/agents/{agent_id}/run` | agents | Create and execute an agent run. |
| GET | `/runs` | runs | List persisted runs. |
| GET | `/runs/{run_id}` | runs | Get a rehydrated run with trace records. |
| GET | `/runs/{run_id}/steps` | runs | Get run step trace records. |
| GET | `/runs/{run_id}/tool-calls` | runs | Get run tool call trace records. |
| GET | `/runs/{run_id}/artifacts` | runs | Get run artifacts. |
| POST | `/runs/{run_id}/cancel` | runs | Mark a run as cancelled. |
| GET | `/approvals/pending` | approvals | List pending approval requests. |
| POST | `/approvals/{approval_id}/approve` | approvals | Approve an approval request. |
| POST | `/approvals/{approval_id}/reject` | approvals | Reject an approval request. |
| GET | `/autoresearch/domains/{domain_id}/targets` | autoresearch | Get default measurable improvement targets for a domain. |
| POST | `/autoresearch/domains/{domain_id}/plan` | autoresearch | Generate a fixed-budget domain improvement plan. |
| POST | `/autoresearch/domains/{domain_id}/improvement-run` | autoresearch | Generate snapshots, measurements, metric comparison, and keep/discard decision for domain assets. |
| POST | `/documents/ingest` | documents, rag | Ingest a text document. |
| POST | `/documents/upload` | documents, rag | Alias for JSON document ingest in v0.1. |
| GET | `/documents` | documents, rag | List ingested documents. |
| GET | `/documents/{document_id}` | documents, rag | Get one ingested document. |
| POST | `/rag/search` | documents, rag | Search ingested chunks. |
| GET | `/tools` | tools | List registered tool contracts. |
| GET | `/tools/{tool_id}` | tools | Get one tool contract. |
| POST | `/tools/{tool_id}/test` | tools | Run a registered tool handler directly. |
| POST | `/obsidian/notes` | obsidian | Create an Obsidian note payload or write to the configured vault. |
| GET | `/obsidian/notes/search` | obsidian | Search notes through the configured Obsidian adapter. |
| POST | `/obsidian/agent-run-note` | obsidian | Create an agent-run note payload. |
| POST | `/evals/run/{run_id}` | evals | Return evaluation records for a run. |
| GET | `/evals/reports` | evals | Return a persisted evaluation report summary. |
| GET | `/evals/{run_id}` | evals | Return evaluation records for a run. |
| GET | `/use-cases` | use-cases | List built-in user test scenarios. |
| GET | `/use-cases/{use_case_id}` | use-cases | Get one user test scenario. |
| POST | `/use-cases/{use_case_id}/run` | use-cases | Execute one built-in user test scenario. |

## Request Schemas

### `RunAgentRequest`

```json
{
  "input_payload": {}
}
```

The exact `input_payload` fields depend on the selected agent contract.

### `IngestRequest`

```json
{
  "title": "string",
  "content": "string",
  "metadata": {}
}
```

### `AutoresearchPlanRequest`

```json
{
  "budget_minutes": 30,
  "primary_metric": "eval_pass_rate",
  "targets": [
    {
      "asset_type": "agent_contract|prompt_template|tool_policy|eval_rubric|domain_contract",
      "asset_id": "string",
      "path": "string",
      "objective": "string",
      "measurements": []
    }
  ]
}
```

### `SearchRequest`

```json
{
  "query": "string",
  "limit": 5
}
```

### `ToolTestRequest`

```json
{
  "input_payload": {}
}
```

### `NoteRequest`

```json
{
  "title": "string",
  "body": "string",
  "folder": "00_Inbox"
}
```

## Main Response Shapes

### Agent Run

```json
{
  "id": "string",
  "tenant_id": "string",
  "user_id": "string",
  "domain_id": "string",
  "agent_id": "string",
  "status": "completed|failed|cancelled",
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
  "started_at": "ISO-8601 string",
  "completed_at": "ISO-8601 string",
  "created_at": "ISO-8601 string",
  "updated_at": "ISO-8601 string",
  "steps": [],
  "tool_calls": [],
  "artifacts": [],
  "evaluations": []
}
```

### Step Trace

```json
{
  "id": "string",
  "run_id": "string",
  "step_index": 0,
  "step_id": "understand_request",
  "name": "understand_request",
  "step_type": "agent_reasoning|tool_call|workflow",
  "input_payload": {},
  "status": "completed",
  "output_payload": {},
  "error_message": null
}
```

### Tool Call Trace

```json
{
  "id": "string",
  "run_id": "string",
  "step_id": "string|null",
  "tool_name": "obsidian.write_note",
  "tool_version": "0.1.0",
  "input_payload": {},
  "output_payload": {},
  "risk_level": "low|medium|high|critical",
  "approval_required": false,
  "approval_status": "not_required|pending",
  "latency_ms": 0,
  "error_message": null,
  "created_at": "ISO-8601 string"
}
```

### Approval Request

```json
{
  "id": "string",
  "run_id": "string",
  "tool_id": "string",
  "reason": "string",
  "status": "pending|approved|rejected"
}
```

### RAG Search Result

```json
{
  "chunk_id": "string",
  "source_metadata": {},
  "score": 1.0,
  "citation_id": "cite:chunk-id",
  "confidence": 0.7,
  "text": "string"
}
```

## Notes

This specification reflects the current v0.1 implementation. Some response schemas are intentionally broad in OpenAPI because several internal contracts are still dynamic dictionaries loaded from YAML. Future work should replace broad `dict` responses with explicit Pydantic response models.
