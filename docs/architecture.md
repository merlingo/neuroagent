# NeuroAgent Architecture

Last updated: 2026-06-11

NeuroAgent is a governed runtime for domain-specific AI agents. The framework is designed around
contracts, explicit workflows, traceable execution, tenant-aware persistence, model-provider
abstraction, RAG, tool governance, evaluations, and local-first memory through Obsidian.

The core principle is simple: the runtime is domain-agnostic, and domain behavior is loaded from
contracts.

## System Overview

```text
Client / API Consumer
        |
        v
FastAPI API Layer
        |
        +-- Domain and tool discovery
        +-- Agent run submission
        +-- Run trace retrieval
        +-- Document ingestion and RAG search
        +-- Approval transitions
        +-- Storage and model status
        |
        v
Agent Runtime
        |
        +-- Contract validation
        +-- Simple planner
        +-- Step executor
        +-- Tool executor and approval gate
        +-- Model gateway
        +-- Artifact writer
        +-- Evaluation runner
        |
        v
Repository Interface
        |
        +-- In-memory repository for development/tests
        +-- SQLAlchemy/Postgres repository for production metadata
        |
        v
Storage Backends
        |
        +-- Postgres for metadata and trace records
        +-- Qdrant for vectors
        +-- S3/MinIO for large artifacts
        +-- Redis for future queues/cache/job state
        +-- Obsidian vault for local-first memory
```

## Layer Responsibilities

### API Layer

The API layer exposes the framework through FastAPI. It should remain thin: routes validate request
shape, select dependencies, call runtime/services, and return serialized dictionaries or Pydantic
models.

Current API groups:

- Domains and agents: list and inspect loaded YAML contracts.
- Runs: list, fetch, cancel, and inspect steps/tool calls/artifacts.
- Tools and approvals: inspect tools and approve/reject pending requests.
- Documents and RAG: ingest documents and search for cited evidence.
- Evals: list run evaluation results.
- Obsidian: produce note payloads and search stubs.
- Use cases: execute bundled demo flows.
- Storage and models: inspect active persistence and model-provider configuration.

Design rule: routes should not own domain logic, tool logic, persistence details, or provider-specific
model code.

### Runtime Layer

The runtime executes one agent run at a time:

1. Load the agent contract from the domain registry.
2. Validate `input_payload` against the agent input schema.
3. Create an execution plan.
4. Execute plan steps through deterministic step handling and governed tool calls.
5. Call the model gateway for final structured output.
6. Validate model output against the agent output schema.
7. Persist the run, steps, tool calls, artifacts, and evaluations.
8. Return a rehydrated run response.

The runtime does not know which provider serves the model and does not know whether persistence is
in-memory or Postgres-backed.

### Contracts and Domain Stacks

Contracts are the boundary between the domain-specific world and the reusable runtime.

Core contract types:

- `AgentContract`: agent ID, role, goal, domain, schemas, tools, approval needs, eval rules.
- `ToolContract`: tool ID, risk level, approval behavior, input/output schemas, allowed domains.
- `DomainContract`: domain ID, name, status, agents, tools, memory scope, risk policy.
- `WorkflowContract`: reusable deterministic workflow definitions.
- `ArtifactContract`: structured artifact metadata and content.
- `EvalContract`: evaluation checks and rubric definitions.

Domain stacks are YAML-backed. The current repository includes research, cybersecurity,
productivity, and investor/GTM domains. The runtime must never hard-code domain behavior.

### Tool and Governance Layer

Tools are registered through contracts and executed through `ToolExecutor`.

Risk handling:

- Low-risk tools may execute directly if allowed by domain/agent policy.
- Forbidden tools are blocked.
- High-risk tools create approval requests instead of executing immediately.
- Tool calls are persisted as trace records with inputs, outputs, risk, approval state, latency, and errors.

The approval model is intentionally explicit. The framework should not silently execute risky
external actions.

### Model Gateway Layer

The model gateway abstracts provider-specific APIs behind one interface:

```text
complete(agent, plan, input_payload, findings) -> ModelResponse
```

Supported provider modes:

- `stub`: deterministic local output for tests and development.
- `openai` / `chatgpt`: OpenAI API through the Responses API.
- `openrouter`: OpenAI-compatible chat completions.
- `anthropic` / `claude`: Claude Messages API.
- `gemini`: Gemini `generateContent`.
- `ollama`: local models through Ollama's OpenAI-compatible API.

Selection is environment-driven through `MODEL_PROVIDER`. Request-level model override is not part
of the current design; this keeps execution reproducible and easier to audit.

Model output rule:

- Providers must return a JSON object.
- The runtime validates the object against the agent output schema.
- Invalid JSON or schema-invalid output fails the run and persists the error.

Local model rule:

- Ollama runs in Docker.
- Model pulls are optional and profile-driven.
- Model tag aliases are configurable because local model availability varies by registry and hardware.

### Persistence Layer

The repository interface is the persistence boundary. Runtime and routes call repository methods,
not SQLAlchemy directly.

Backends:

- `InMemoryRepository`: development and test fallback.
- `SQLAlchemyRepository`: production metadata persistence in Postgres.

Selection:

- `REPOSITORY_BACKEND=memory|postgres`.
- Development without `DATABASE_URL` can use memory fallback.
- Production with Postgres selected must fail fast if `DATABASE_URL` is missing.

Persisted record groups:

- Runtime: runs, steps, tool calls, artifacts, approvals, audit logs.
- Domain stack: domain stacks, agent definitions, prompt templates, tool definitions, policies.
- RAG: documents, chunks, embedding records, retrieval events planned for future expansion.
- Evaluation: evaluation runs and results.
- Memory: Obsidian note records.

Tenant rule:

- Tenant-scoped records must carry `tenant_id`.
- API key authentication resolves tenant identity and tenant-scoped routes enforce access.

### RAG and Knowledge Layer

Postgres is the source of truth for document and chunk metadata. Qdrant is the primary vector
backend for retrieval.

Current state:

- Documents can be ingested.
- Text is chunked.
- Metadata and chunks can be persisted through the repository.
- Lexical search fallback exists.
- Qdrant adapter exists.

Target production path:

1. Ingest document.
2. Persist document metadata in Postgres.
3. Chunk document and persist chunks.
4. Generate embeddings.
5. Upsert vectors into Qdrant with tenant/domain/document/chunk payload.
6. Persist embedding records in Postgres.
7. Search Qdrant with tenant/domain filters.
8. Hydrate matching chunks from Postgres.
9. Return cited evidence.

### Artifact Storage

Artifacts are metadata records plus either inline content or an external `storage_uri`.

Rules:

- Small artifacts may be stored inline.
- Large artifacts are written to S3/MinIO through the object storage adapter when DB-backed persistence externalizes content.
- All artifacts should remain queryable through run trace endpoints.
- In-memory development mode uses a deterministic `memory://` fallback for externalized artifacts.

### Obsidian Memory Layer

Obsidian is intended as a local-first memory and research workspace, not just a text dump.

Target behavior:

- Write run notes with safe frontmatter.
- Link notes to `run_id`, `agent_id`, `domain_id`, and artifacts.
- Search notes through the Obsidian adapter.
- Persist note write status in `obsidian_note_records`.

Current behavior:

- Templates, schemas, vault structure, Dockerized Obsidian, mounted vaults, disabled-mode note payloads, and enabled-mode file writes/search exist.
- Obsidian Local REST API plugin automation remains optional future work.

### Evaluation and AutoResearcher

Evaluations are first-class runtime artifacts. Each run can produce evaluation results that verify
schema validity, evidence behavior, policy compliance, and domain-specific quality.

AutoResearcher is a separate layer for fixed-budget improvement of measurable assets:

- agent contracts,
- prompts,
- tool policies,
- domain contracts,
- eval rubrics,
- benchmark datasets.

Current behavior:

- AutoResearcher planning artifacts exist.
- AutoResearcher can build an asset improvement package with editable targets, asset snapshots,
  deterministic validation measurements, metric comparison, and a keep/discard decision.
- Automatic patch application is intentionally outside this phase. The framework produces a
  measurable package that can be reviewed, persisted as artifacts, or used by a future worker.

## Core Data Flow

### Agent Run Flow

```text
POST /agents/{agent_id}/run
        |
        v
Load agent contract
        |
        v
Validate input schema
        |
        v
Create plan
        |
        v
Execute steps and governed tools
        |
        v
Call model gateway
        |
        v
Validate output schema
        |
        v
Persist run trace, artifact, eval results
        |
        v
Return hydrated run
```

### Approval Flow

```text
Tool call requested
        |
        v
Tool policy evaluates risk and allowlist
        |
        +-- Allowed low-risk tool -> execute and trace
        |
        +-- High-risk tool -> create approval request
        |
        +-- Forbidden tool -> block and audit
```

### Model Provider Flow

```text
Runtime
        |
        v
ModelGatewayFactory reads MODEL_PROVIDER
        |
        +-- stub
        +-- openai/chatgpt
        +-- openrouter
        +-- anthropic/claude
        +-- gemini
        +-- ollama
        |
        v
Provider call returns JSON text
        |
        v
Parse JSON object
        |
        v
Runtime validates output contract
```

### AutoResearch Asset Improvement Flow

AutoResearcher improves framework assets through a bounded, measurable loop. It is not a normal
agent run and it does not bypass governance. Its job is to identify editable assets, produce an
experiment program, evaluate the candidate package, and return a reviewable decision artifact.

```text
POST /autoresearch/domains/{domain_id}/improvement-run
        |
        v
Validate domain exists in the domain registry
        |
        v
Resolve editable targets
        |
        +-- request targets supplied by caller
        +-- default targets discovered from domain contracts, agent contracts,
            prompt templates, tool policy, and eval validators
        |
        v
Render fixed-budget autoresearch program
        |
        v
Snapshot target assets
        |
        +-- enforce project-root path containment
        +-- record existence, size, SHA-256 content hash, and summary
        |
        v
Validate measurable assets
        |
        +-- domain contracts through `DomainContract`
        +-- agent contracts through `AgentContract`
        +-- tool policies through YAML parsing
        +-- prompts and eval assets through non-empty content checks
        |
        v
Compute measurement results
        |
        +-- contract_validity
        +-- eval_pass_rate proxy
        +-- trace_completeness
        +-- optional custom primary metric mapped to the eval proxy
        |
        v
Build metric comparison and keep/discard decision
        |
        v
Return improvement package
```

The response is an `AutoresearchImprovementRun` with:

- `run_id`: an autoresearch-specific identifier.
- `plan`: the editable targets, fixed context, primary metric, acceptance rule, and generated
  `program.md`.
- `asset_snapshots`: target path, existence, hash, size, and a compact summary.
- `measurement_results`: metric score, baseline, target, pass/fail, and finding.
- `keep_decision`: `keep`, `discard`, or `needs_review`.
- `artifacts`: `program.md`, `experiment_plan.json`, `measurement_rubric.json`,
  `improvement_backlog.md`, `asset_snapshots.json`, `measurement_results.json`,
  `metric_comparison.json`, and `keep_discard_decision.json`.

Framework usage:

- Use `GET /autoresearch/domains/{domain_id}/targets` to inspect the default asset boundary before
  launching an experiment.
- Use `POST /autoresearch/domains/{domain_id}/plan` when only the program, backlog, and rubric are
  needed.
- Use `POST /autoresearch/domains/{domain_id}/improvement-run` when the framework should evaluate
  the current or proposed asset package and produce a keep/discard decision.
- Store returned artifacts through the artifact writer or a future `autoresearch_experiments`
  table when the run must be retained beyond the API response.
- Review and apply code changes through the normal repository workflow. AutoResearcher should not
  write arbitrary files or weaken tool governance as part of the automatic loop.

## Design Decisions

### DD-001: Domain-Agnostic Core Runtime

Decision: keep the runtime independent of domain-specific behavior.

Reason: domain stacks should be replaceable without changing runtime code.

Consequence: domain behavior must be expressed through YAML contracts, tool contracts, schemas,
policies, prompts, and evals.

### DD-002: Contracts Over Implicit Prompts

Decision: use explicit Pydantic/YAML contracts for agents, domains, tools, workflows, artifacts,
and evals.

Reason: contracts make behavior testable, auditable, and versionable.

Consequence: every agent run validates input and output against schemas.

### DD-003: Explicit Workflows Before Autonomous Loops

Decision: prefer deterministic workflows and bounded plan steps over unbounded autonomous loops.

Reason: this improves traceability, governance, and failure handling.

Consequence: open-ended reasoning is allowed, but external actions remain governed and explicit.

### DD-004: Repository Interface as Persistence Boundary

Decision: runtime and routes depend on a repository interface rather than direct SQLAlchemy access.

Reason: tests and local development need a memory backend, while production needs Postgres.

Consequence: new persistence behavior should be added to the repository interface first, then
implemented in both memory and SQL backends.

### DD-005: Postgres as Metadata Source of Truth

Decision: store canonical metadata in Postgres.

Reason: runs, artifacts, documents, approvals, evals, and audit logs need relational queries,
durability, and migrations.

Consequence: Qdrant and S3/MinIO are supporting storage systems, not canonical metadata stores.

### DD-006: Qdrant as Primary Vector Backend

Decision: use Qdrant as the primary vector search backend.

Reason: Qdrant is purpose-built for vector search and keeps vector operations separate from
metadata persistence.

Consequence: vector payloads must contain enough IDs to hydrate results from Postgres.

### DD-007: Inline Small Artifacts, Externalize Large Artifacts

Decision: store small artifacts inline and large artifacts in S3/MinIO.

Reason: small trace artifacts are convenient in Postgres, but large files should not bloat the DB.

Consequence: artifact records must always include metadata and may include either `content` or
`storage_uri`.

### DD-008: Provider-Agnostic Model Gateway

Decision: model providers are hidden behind `ModelGateway`.

Reason: the framework must support local and remote models without changing runtime code.

Consequence: provider-specific request/response parsing belongs in gateway adapters.

### DD-009: Stub Gateway Remains the Default

Decision: keep `MODEL_PROVIDER=stub` as the default.

Reason: tests and local development should not require network access or API keys.

Consequence: production environments must explicitly choose a real provider.

### DD-010: Environment-Driven Model Selection

Decision: model provider and model name are selected through environment settings, not per-run
request overrides.

Reason: environment selection is easier to audit and reproduce.

Consequence: future UI/admin model selection should be designed as a separate governed feature.

### DD-011: Human Approval for Risky Actions

Decision: high-risk tool calls create approval requests instead of executing automatically.

Reason: the framework is designed for governed agents, not uncontrolled automation.

Consequence: approval routes and audit logs are part of the core runtime surface.

### DD-012: Tenant ID on Tenant-Scoped Records

Decision: tenant-scoped data must carry `tenant_id`.

Reason: tenant isolation must be enforced consistently across runs, approvals, documents, RAG,
evals, and admin operations.

Consequence: routes preserve tenant fields and reject cross-tenant access unless an admin API key is used.

### DD-013: Obsidian as Local-First Memory

Decision: Obsidian is treated as a memory workspace and audit-friendly note layer.

Reason: users need inspectable, local-first research records, not only API responses.

Consequence: note records should link back to run artifacts and retain write status.

### DD-014: AutoResearcher as First-Class Improvement Layer

Decision: AutoResearcher is part of the framework, not a separate experiment script.

Reason: domain stacks need measurable, repeatable improvement loops.

Consequence: AutoResearcher runs produce programs, rubrics, target references, snapshots, metrics,
and keep/discard decisions. A future persistence table should retain these packages beyond the API
response when experiments become long-running jobs.

### DD-015: Docker Compose First, Kubernetes Later

Decision: local/MVP deployment uses Docker Compose.

Reason: the framework currently needs developer-friendly local orchestration for Postgres, Redis,
Qdrant, MinIO, Ollama, and Obsidian.

Consequence: Kubernetes and hosted deployment profiles should come after API behavior stabilizes.

## Current Boundaries and Risks

- API key authentication is implemented; JWT/OIDC and richer service-account models remain future options.
- Qdrant retrieval is wired into `/rag/search` with repository metadata hydration and lexical fallback.
- Obsidian REST plugin automation is not enabled by default; mounted-vault file writes/search are available.
- Remote model provider behavior depends on API keys, quotas, model availability, and provider
  response quality.
- Local Ollama model behavior depends on local hardware and model tag availability.
- Cost estimates are not provider-price accurate.

## Near-Term Architecture Priorities

1. Add Obsidian Local REST API plugin automation if direct vault file operations are insufficient.
2. Move long-running jobs to workers.
3. Add observability, metrics, and cost reporting.
4. Persist AutoResearcher improvement runs in an `autoresearch_experiments` table.
5. Add a worker-backed AutoResearcher execution mode that can generate candidate patches and run
   full regression/eval suites before returning a keep/discard decision.
