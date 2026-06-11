# NeuroAgent Framework User Guide

Version: `0.1.0`

Local API:

```text
http://127.0.0.1:8011
```

## What You Can Test Today

This version is a backend foundation for governed, domain-specific AI agents. It currently supports domain discovery, agent runs, trace retrieval, document ingestion, repository-backed RAG metadata, lexical RAG fallback, Autoresearch domain-improvement plans, Obsidian note payloads or vault writes, model provider configuration, storage status, and a built-in use case catalog.

The runtime uses a stub model gateway and in-memory repository by default. Postgres persistence and real model providers can be enabled through environment configuration.

## Start the API

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8011
```

Check health:

```bash
curl http://127.0.0.1:8011/health
```

## Recommended First Path

List use cases:

```bash
curl http://127.0.0.1:8011/use-cases
```

Inspect one use case:

```bash
curl http://127.0.0.1:8011/use-cases/cybersecurity-sigma-run
```

Run it:

```bash
curl -X POST http://127.0.0.1:8011/use-cases/cybersecurity-sigma-run/run
```

Copy the returned `result.id`, then inspect trace records:

```bash
curl http://127.0.0.1:8011/runs/{run_id}
curl http://127.0.0.1:8011/runs/{run_id}/steps
curl http://127.0.0.1:8011/runs/{run_id}/tool-calls
curl http://127.0.0.1:8011/runs/{run_id}/artifacts
curl http://127.0.0.1:8011/evals/{run_id}
```

## Discovery

```bash
curl http://127.0.0.1:8011/domains
curl http://127.0.0.1:8011/agents
curl http://127.0.0.1:8011/tools
```

## Manual Agent Runs

Research agent:

```bash
curl -X POST http://127.0.0.1:8011/agents/research.literature_researcher/run \
  -H "Content-Type: application/json" \
  -d '{"input_payload": {"research_question": "Agentic research governance for domain-specific AI systems"}}'
```

Sigma agent:

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

## RAG Testing

```bash
curl -X POST http://127.0.0.1:8011/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sigma Behavioral Vectors",
    "content": "Sigma rules can represent behavioral threat vectors for detection engineering.",
    "metadata": {"source_type": "local", "domain_id": "cybersecurity"}
  }'

curl -X POST http://127.0.0.1:8011/rag/search \
  -H "Content-Type: application/json" \
  -d '{"query": "behavioral threat vectors", "limit": 5}'
```

## Autoresearch Domain Improvement

```bash
curl http://127.0.0.1:8011/autoresearch/domains/cybersecurity/targets

curl -X POST http://127.0.0.1:8011/autoresearch/domains/cybersecurity/plan \
  -H "Content-Type: application/json" \
  -d '{"budget_minutes": 30, "primary_metric": "eval_pass_rate", "targets": []}'
```

The plan response includes `program_markdown`, `experiment_plan.json`, `measurement_rubric.json`, and `improvement_backlog.md`.

## Obsidian Note Stub

```bash
curl -X POST http://127.0.0.1:8011/obsidian/notes \
  -H "Content-Type: application/json" \
  -d '{"title": "NeuroAgent Test Note", "body": "This is a local-first note stub.", "folder": "00_Inbox"}'
```

## What Good Looks Like

- `/health` returns `ok`.
- `/domains` returns at least `research` and `cybersecurity`.
- Agent runs return `status: completed`.
- Run details include `steps`, `artifacts`, and `evaluations`.
- RAG search returns a `citation_id` after ingesting a matching document.
- Autoresearch plan returns `program.md` and measurement artifacts.

## Current Limitations

- API key authentication is available through `API_AUTH_ENABLED=true`, `API_KEYS`, and `ADMIN_API_KEYS`.
- Postgres persistence is available, but live restart scenarios require a configured database.
- Real model providers are available, but live calls require API keys or a pulled Ollama model.
- `/rag/search` uses vector retrieval when Qdrant is configured and falls back to lexical repository search when vector results are unavailable.
- Obsidian can write/search the mounted vault when `OBSIDIAN_ENABLED=true`; Local REST API plugin automation is not enabled by default.
- Use-case catalog is a test harness, not a production workflow engine.
