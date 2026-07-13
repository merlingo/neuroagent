# NeuroAgent Framework

Production-oriented framework for governed, domain-specific AI agents with RAG, tool policy, Obsidian memory, evaluations, and traceable runtime artifacts.

This repository follows `neuroagent_framework_infrastructure.md` as the initial architectural source of truth.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
make test
make dev
```

API health:

```bash
curl http://127.0.0.1:8000/health
```

## User Documentation

- API guide: `docs/api-guide.md`
- User guide: `docs/user-guide.md`
- User test scenarios: `docs/user-test-scenarios.md`
- OpenAPI spec: `docs/openapi.json`

## Current Scope

Implemented foundation:

- FastAPI app with health, domains, agents, runs, tools, documents, Autoresearch, use cases, Obsidian, and eval routes.
- Pydantic v2 contracts for agents, tools, workflows, domains, evals, and artifacts.
- YAML-backed domain and tool registries.
- Deterministic stub runtime that validates input, builds a plan, executes governed tool steps, writes artifacts, and evaluates runs.
- Configurable model gateway for stub, OpenAI/ChatGPT API, OpenRouter, Claude, Gemini, and local Ollama-backed models.
- In-memory repositories for early development and tests.
- Seed research and cybersecurity stacks.
- Docker Compose for API, worker, Postgres, Redis, Qdrant, MinIO, Ollama, and Obsidian.

Persistent database migrations, Qdrant integration, and model provider adapters are scaffolded.
Obsidian now runs as a separate Docker Compose service with a mounted NeuroAgent vault; real REST
plugin automation remains optional because the framework can write/search the mounted vault directly.

## Model Providers

The default model provider is `stub`, so local tests do not require API keys.

```bash
curl http://127.0.0.1:8000/models/status
```

Set `MODEL_PROVIDER` to `openai`, `openrouter`, `anthropic`, `gemini`, or `ollama` to use a real provider. Local models run through Ollama:

```bash
docker compose up ollama
docker compose --profile ollama-pull run --rm ollama-pull
```

Use `OLLAMA_MODEL` to select the active local model. The example env file includes aliases for DeepSeek-R1, Kimi K2.6, GLM-5.1, Qwen 3.5, Qwen2.5-Coder, and Gemma 4.

## API Keys

Local development leaves API auth disabled by default. To enable tenant-scoped API keys:

```env
API_AUTH_ENABLED=true
API_KEYS=tenant-a-key:tenant-a
ADMIN_API_KEYS=admin-key
```

Send keys with `X-API-Key`.

## Obsidian

Run Obsidian with the rest of the local stack:

```bash
docker compose up obsidian
```

The web UI is exposed on `http://127.0.0.1:3000`. The mounted vault lives at
`app/obsidian/vaults/NeuroAgentVault`.

## Loop Engineering Integration

NeuroAgent exposes request/response capabilities for Intravision's Loop Engineering feature — a durable meta-orchestration layer that runs many sequential agent iterations toward a long-term goal.

### Per-request model override

Pass `"model": "gpt-4.1-mini"` in the run request. Validated against `NEUROAGENT_ALLOWED_MODELS` (comma-separated env var). Unknown models return 422.

### Structured run result

Every run response includes a `result` object:

```json
{
  "status": "completed | max_steps | max_tokens | error",
  "final_answer": "...",
  "summary": "3-5 sentence model-generated summary",
  "artifacts": [{"type": "...", "ref": "...", "description": "..."}],
  "tool_calls": [{"tool": "...", "count": 1}],
  "usage": {"prompt_tokens": 100, "completion_tokens": 50, "steps": 3}
}
```

### Loop context injection

Pass `loop_context` in the run request to inject goal, state document, and prior summaries into the system prompt:

```json
{
  "loop_context": {
    "loop_id": "loop-abc",
    "iteration_index": 3,
    "goal": "Fix the auth bug",
    "state_document": "...",
    "prior_summaries": ["Iteration 1: ...", "Iteration 2: ..."]
  }
}
```

`loop_id` and `iteration_index` are echoed back in the response for correlation.

### Per-request budgets

Pass `max_steps` and/or `max_tokens` to override env defaults. On breach, the run terminates gracefully with `result.status` set to `"max_steps"` or `"max_tokens"`.

### Critic endpoint

`POST /v1/evaluate` — single LLM call that evaluates iteration progress:

```json
{
  "goal": "...",
  "state_document": "...",
  "iteration_summary": "...",
  "recent_verdicts": ["..."]
}
```

Returns `{ progress, confidence, stall_signals, recommendation, reasoning }`.

### Idempotency

Pass `client_run_id` in the run request. Duplicates within 10 minutes return 409.

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEUROAGENT_ALLOWED_MODELS` | (empty) | Comma-separated model allowlist |
| `NEUROAGENT_LOOP_CONTEXT_MAX_CHARS` | 24000 | Max chars for injected loop context |
| `NEUROAGENT_CRITIC_MODEL` | gpt-4.1-mini | Model used for summaries and /v1/evaluate |
| `NEUROAGENT_DEFAULT_MAX_STEPS` | 20 | Default step budget per run |
| `NEUROAGENT_DEFAULT_MAX_TOKENS` | 100000 | Default token budget per run |

# neuroagent
