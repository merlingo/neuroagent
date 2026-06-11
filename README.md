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

# neuroagent
