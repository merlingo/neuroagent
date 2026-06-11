# NeuroAgent Roadmap

Last updated: 2026-06-09

This roadmap reflects the current repository state and the production architecture described in
`neuroagent_framework_infrastructure.md`. It is intentionally implementation-oriented: each phase
should be small enough to verify with tests and user scenarios.

## Current State

Completed or substantially implemented:

- FastAPI backend with health, domain, agent, run, tool, approval, document, RAG, Obsidian, eval, storage, model, and use-case routes.
- Pydantic v2 contracts for agents, tools, workflows, domains, evals, and artifacts.
- YAML-backed domain and tool registries.
- Domain stacks for research, cybersecurity, productivity, and investor/GTM.
- Governed runtime with input validation, planning, tool execution, artifacts, evaluations, and trace rehydration.
- Tool policy checks, approval requests, and tool call tracing.
- In-memory repository for development/tests.
- SQLAlchemy repository adapter and Alembic initial schema for runtime, RAG metadata, approvals, artifacts, evals, audit logs, contracts, tenants, users, and Obsidian note records.
- Configurable model gateway for `stub`, OpenAI/ChatGPT API, OpenRouter, Claude/Anthropic, Gemini, and local Ollama.
- Docker Compose services for API, worker, Postgres, Redis, Qdrant, MinIO, Ollama, and Obsidian.
- Document ingestion, chunking, repository-backed metadata, lexical search fallback, Qdrant adapter, and vector-backed API search path.
- S3/MinIO object writer path for large artifacts, with hash/size metadata and inline fallback.
- AutoResearcher v0.1 planning artifacts.
- Obsidian Docker service, mounted NeuroAgent vault, and file-backed note write/search adapter.
- OpenAPI generation, user test scenarios, and unit tests.

Known gaps:

- API key authentication and tenant enforcement are implemented for tenant-scoped API routes.
- Live Qdrant smoke tests require a running Qdrant service; tests cover payloads, filters, indexing, vector search calls, and fallback behavior.
- Obsidian Local REST API plugin automation is not implemented; enabled mode currently uses direct vault file writes/search.
- Live provider smoke tests require API keys and local model availability.
- Worker queue execution is scaffolded but not the primary runtime path.
- Observability and cost governance are still basic.

## Phase 1: Production RAG Path

Status: implemented in the API path with lexical fallback.

Goal: make Qdrant the real retrieval backend while keeping Postgres as the metadata source of truth.

Work:

- Generate embeddings during document ingestion.
- Ensure Qdrant collections using model-aware collection names.
- Upsert chunk vectors with payload fields: `tenant_id`, `domain_id`, `document_id`, `chunk_id`, `source_uri`, `title`, `hash`, and `embedding_model`.
- Persist embedding records in Postgres.
- `/rag/search` embeds the query, searches Qdrant with tenant/domain filters, hydrates chunks from repository metadata, and returns cited evidence.
- Keep lexical in-memory search as development fallback.

Acceptance criteria:

- Ingested documents produce Postgres metadata and Qdrant vectors.
- Search results are tenant-isolated.
- Returned evidence includes chunk IDs, source metadata, score, citation ID, confidence, and text.
- Tests cover Qdrant payload construction, filter construction, metadata hydration, and fallback behavior.

## Phase 2: Artifact Object Storage

Status: implemented for S3-compatible writes and deterministic memory fallback.

Goal: make large artifacts durable outside Postgres.

Work:

- S3/MinIO artifact writer exists.
- Small artifact content stays inline when below `ARTIFACT_INLINE_MAX_BYTES`.
- Large artifact content is serialized, written through object storage, and persisted with `storage_uri`, content hash, size, and metadata.
- Object read/download behavior can be added when routes need direct artifact downloads.
- Missing S3 settings produce explicit errors for DB-backed large artifact writes.

Acceptance criteria:

- Small artifacts remain inline.
- Large artifacts are written to MinIO/S3.
- Run traces and artifacts survive API restart.
- Tests cover inline, external, missing config, and metadata behavior.

## Phase 3: Authentication and Tenant Enforcement

Status: implemented with API keys; JWT/OIDC can be added later if needed.

Goal: protect tenant-scoped data and admin operations.

Work:

- API key auth uses `X-API-Key`.
- `API_KEYS` maps `key:tenant_id` entries.
- `ADMIN_API_KEYS` grants admin access.
- Tenant filters are enforced for runs, documents, RAG search, approvals, evals, and admin seed access.
- Service-account/JWT support can be added later if worker/API internal calls need identity separation.

Acceptance criteria:

- Tenant A cannot access Tenant B data.
- Admin endpoints require admin authorization.
- Health and public documentation remain accessible without auth.
- Tests cover cross-tenant access denial and admin authorization.

## Phase 4: Real Obsidian Integration

Status: Docker service and file-backed vault adapter are implemented; REST plugin automation remains optional future work.

Goal: turn Obsidian from a stubbed note payload layer into a real local-first memory adapter.

Work:

- Implement Obsidian REST client write, read, and search operations if REST semantics are required beyond mounted-vault file operations.
- Map agent run artifacts into note templates with safe frontmatter.
- Persist `obsidian_note_records` with write status and linked artifact IDs.
- Add retry/error handling and clear disabled-mode behavior.

Acceptance criteria:

- Notes can be written to a configured vault.
- Note records link `run_id`, `agent_id`, `domain_id`, vault name, path, frontmatter, write status, and artifact.
- Obsidian-disabled mode remains deterministic and testable.
- Tests mock HTTP calls and verify frontmatter safety.

## Phase 5: Worker-Backed Long-Running Jobs

Goal: move slow work off synchronous request paths.

Work:

- Use Redis-backed workers for document ingestion, embeddings, eval suites, and AutoResearcher experiments.
- Add job creation and status endpoints.
- Persist job lifecycle events in audit logs.
- Add retry, timeout, and cancellation policies.

Acceptance criteria:

- API can enqueue and track long-running work.
- Worker restarts do not lose persisted job state.
- Failed jobs retain traceable error context.

## Phase 6: Evaluation and AutoResearcher Expansion

Goal: make domain improvement measurable and repeatable.

Work:

- Add eval datasets and benchmark snapshots.
- Persist AutoResearcher experiments with program, plan, rubric, backlog, metric comparison, keep/discard decision, and target asset references.
- Add domain-specific eval suites for research and cybersecurity.
- Add regression checks for prompt, policy, and contract changes.

Acceptance criteria:

- AutoResearcher can compare a proposed asset change against a baseline.
- Keep/discard decisions reference metrics and artifacts.
- Eval results are queryable by run, domain, agent, and dataset version.

## Phase 7: Observability, Cost, and Governance

Goal: make runtime behavior inspectable and governable in production.

Work:

- Add structured logs and trace IDs across API, runtime, tools, model calls, storage, and workers.
- Add OpenTelemetry-compatible hooks.
- Track model latency, token usage, and estimated cost by tenant/domain/agent/model.
- Expand audit logs for policy blocks, approvals, rejected tool calls, and model failures.
- Add red-team and guardrail reporting.

Acceptance criteria:

- Operators can trace a run across all subsystems.
- Cost and token usage can be summarized by tenant and model.
- Policy decisions are auditable.

## Phase 8: Production Deployment Hardening

Goal: prepare the framework for production operation.

Work:

- Add CI checks for tests, schema migration, docs, and OpenAPI drift.
- Add migration tests against a real Postgres instance.
- Add backup/restore guidance for Postgres, Qdrant, MinIO, and Obsidian records.
- Add rate limiting and request size limits.
- Add secrets handling guidance.
- Add local, staging, and production deployment profiles.

Acceptance criteria:

- CI blocks broken tests, schema drift, and OpenAPI drift.
- Production config fails fast on missing required settings.
- Operators have documented backup and restore procedures.
