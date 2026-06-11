# NeuroAgent User Test Scenarios

Base URL:

```text
http://127.0.0.1:8011
```

Record each result as:

```text
PASS / FAIL
Notes:
Run ID:
Unexpected behavior:
```

## Scenario 1: Health and Discovery

```bash
curl http://127.0.0.1:8011/health
curl http://127.0.0.1:8011/domains
curl http://127.0.0.1:8011/agents
curl http://127.0.0.1:8011/tools
```

Expected:

- Health returns `status: ok`.
- Domains include `research`, `cybersecurity`, `productivity`, and `investor_gtm`.
- Agents include `research.literature_researcher` and `cybersecurity.sigma_rule_agent`.

## Scenario 2: Use Case Catalog

```bash
curl http://127.0.0.1:8011/use-cases
curl http://127.0.0.1:8011/use-cases/research-agent-run
```

Expected:

- Catalog includes `research-agent-run`, `cybersecurity-sigma-run`, `rag-ingest-search`, `autoresearch-domain-plan`, and `obsidian-note-stub`.
- A use case includes `request_payload`, `expected_result`, and `follow_up_endpoints`.

## Scenario 3: Research Agent Run

```bash
curl -X POST http://127.0.0.1:8011/use-cases/research-agent-run/run
```

Expected:

- `result.status` is `completed`.
- `result.id` exists.
- `result.steps`, `result.artifacts`, and `result.evaluations` are not empty.

Follow-up:

```bash
curl http://127.0.0.1:8011/runs/{run_id}
curl http://127.0.0.1:8011/runs/{run_id}/steps
curl http://127.0.0.1:8011/evals/{run_id}
```

## Scenario 4: Cybersecurity Sigma Agent Run

```bash
curl -X POST http://127.0.0.1:8011/use-cases/cybersecurity-sigma-run/run
```

Expected:

- `result.status` is `completed`.
- `result.final_output.sigma_rule` exists.
- `result.final_output.false_positive_analysis` exists.
- `result.final_output.confidence_score` exists.

## Scenario 5: Contract Validation Failure

```bash
curl -X POST http://127.0.0.1:8011/agents/cybersecurity.sigma_rule_agent/run \
  -H "Content-Type: application/json" \
  -d '{"input_payload": {"threat_description": "Suspicious PowerShell execution"}}'
```

Expected:

- HTTP status is `400`.
- Error detail mentions `target_platform`.

## Scenario 6: RAG Ingest and Search

```bash
curl -X POST http://127.0.0.1:8011/use-cases/rag-ingest-search/run
```

Expected:

- `result.ingest.document_id` exists.
- `result.search_results[0].citation_id` starts with `cite:`.

## Scenario 7: Autoresearch Domain Improvement Plan

```bash
curl -X POST http://127.0.0.1:8011/use-cases/autoresearch-domain-plan/run
```

Expected:

- `result.program_markdown` exists.
- `result.artifacts` includes `program.md`, `experiment_plan.json`, `measurement_rubric.json`, and `improvement_backlog.md`.

## Scenario 8: Obsidian Note Stub

```bash
curl -X POST http://127.0.0.1:8011/use-cases/obsidian-note-stub/run
```

Expected:

- `result.status` is `stubbed`.
- `result.path` exists.
- `result.content` starts with Markdown frontmatter.

## Scenario 9: Run Cancellation

1. Run Scenario 3 or 4.
2. Copy `run_id`.
3. Cancel it:

```bash
curl -X POST http://127.0.0.1:8011/runs/{run_id}/cancel
```

Expected:

- Response contains `status: cancelled`.
- Trace endpoints still return data.

## Scenario 10: Evaluation Lookup

1. Run Scenario 3 or 4.
2. Copy `run_id`.
3. Fetch evaluations:

```bash
curl http://127.0.0.1:8011/evals/{run_id}
curl -X POST http://127.0.0.1:8011/evals/run/{run_id}
```

Expected:

- Both endpoints return evaluation records.
- Records include `eval_name`, `passed`, `score`, and `rubric`.

## Scenario 11: Storage Status

```bash
curl http://127.0.0.1:8011/storage/status
```

Expected:

- Response includes `database.backend`, `vector.backend`, and `artifacts.inline_max_bytes`.
- In local development without `DATABASE_URL`, `database.backend` can be `memory`.
- In a DB-backed stack, `database.backend` is `postgres`.

## Scenario 12: DB-Backed Run Survives Restart

Prerequisite: start the API with `APP_ENV=production`, `REPOSITORY_BACKEND=postgres`, and `DATABASE_URL` set.

```bash
curl -X POST http://127.0.0.1:8011/use-cases/research-agent-run/run
curl http://127.0.0.1:8011/runs/{run_id}
```

Restart the API process, then run:

```bash
curl http://127.0.0.1:8011/runs/{run_id}
curl http://127.0.0.1:8011/runs/{run_id}/steps
curl http://127.0.0.1:8011/runs/{run_id}/artifacts
```

Expected:

- The run still exists after restart.
- Steps and artifacts are still returned.

## Scenario 13: Persisted Document Metadata Survives Restart

Prerequisite: DB-backed API.

```bash
curl -X POST http://127.0.0.1:8011/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"tenant-a","domain_id":"research","title":"Persistence Note","content":"Persistent RAG chunks should survive API restarts.","metadata":{"source_type":"manual"}}'
curl http://127.0.0.1:8011/documents/{document_id}
```

Restart the API process, then run:

```bash
curl http://127.0.0.1:8011/documents/{document_id}
```

Expected:

- The document metadata and chunks still exist.

## Scenario 14: Tenant-Isolated RAG Search

```bash
curl -X POST http://127.0.0.1:8011/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"tenant-a","domain_id":"research","title":"Tenant A","content":"alpha exclusive research note","metadata":{}}'
curl -X POST http://127.0.0.1:8011/rag/search \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"tenant-a","domain_id":"research","query":"alpha exclusive","limit":5}'
curl -X POST http://127.0.0.1:8011/rag/search \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"tenant-b","domain_id":"research","query":"alpha exclusive","limit":5}'
```

Expected:

- Tenant A search returns cited chunks.
- Tenant B search does not return Tenant A chunks.

## Scenario 15: Artifact Inline vs External Storage

Prerequisite: set `ARTIFACT_INLINE_MAX_BYTES` low enough to force large artifacts out of line, and configure `S3_BUCKET` for DB-backed artifact URIs.

```bash
curl -X POST http://127.0.0.1:8011/use-cases/research-agent-run/run
curl http://127.0.0.1:8011/runs/{run_id}/artifacts
```

Expected:

- Small artifacts include inline `content`.
- Large artifacts have `content: null` and a `storage_uri`.

## Scenario 16: Seed Contracts Into DB

Prerequisite: DB-backed API.

```bash
curl -X POST http://127.0.0.1:8011/admin/db/seed-contracts
```

Expected:

- Response contains `persisted: true`.
- Counts for `domains`, `agents`, `tools`, and `prompts` are greater than zero.

## Scenario 17: Model Provider Status

```bash
curl http://127.0.0.1:8011/models/status
```

Expected:

- Default local development returns `provider: stub`, `model: stub-model`, and `api_key: not_required`.
- Remote providers report `configured` or `missing_key`.
- Ollama provider includes `ollama: reachable` or `ollama: unreachable`.

## Scenario 18: Local Ollama Model Run

Prerequisite: set `MODEL_PROVIDER=ollama` and choose an `OLLAMA_MODEL`.

```bash
docker compose up ollama
docker compose --profile ollama-pull run --rm ollama-pull
curl http://127.0.0.1:8011/models/status
curl -X POST http://127.0.0.1:8011/agents/research.literature_researcher/run \
  -H "Content-Type: application/json" \
  -d '{"input_payload":{"research_question":"local model governance smoke test"}}'
```

Expected:

- `/models/status` reports `provider: ollama`.
- The run records the selected Ollama model in `model`.
- If the model is not pulled or unsupported, the run fails with an actionable provider error.

## Scenario 19: Remote Provider Smoke Tests

Run one provider at a time by setting `MODEL_PROVIDER` and the matching API key.

```bash
curl http://127.0.0.1:8011/models/status
curl -X POST http://127.0.0.1:8011/agents/research.literature_researcher/run \
  -H "Content-Type: application/json" \
  -d '{"input_payload":{"research_question":"remote provider smoke test"}}'
```

Expected:

- `openai` uses `OPENAI_API_KEY` and `DEFAULT_MODEL`.
- `openrouter` uses `OPENROUTER_API_KEY` and `OPENROUTER_MODEL`.
- `anthropic` uses `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL`.
- `gemini` uses `GEMINI_API_KEY` and `GEMINI_MODEL`.
- Missing API keys are reported by `/models/status` and model calls fail fast.

## Issue Report Template

```text
Scenario:
Command:
Expected:
Actual:
Run ID:
Response snippet:
Notes:
```
