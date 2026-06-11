# NeuroAgent Framework — Production-Ready Agentic Infrastructure Blueprint

> Working name: **NeuroAgent Framework**  
> Purpose: Build a sellable, production-ready framework for domain-specific AI agents with RAG, tool governance, Obsidian memory, AutoResearcher workflows, and Codex-friendly development instructions.  
> Primary builder: **Codex / AI coding agent**  
> Owner: **Neurobytes / Mert Nar**  
> Version: `v0.2-roadmap`  
> Last updated: `2026-06-09`

---

## 0. Codex Operating Instructions

Codex must treat this file as the **single architectural source of truth** for the initial implementation.

When implementing this framework:

1. Do **not** build a monolithic chatbot.
2. Build a modular **agent runtime** that can host multiple domain-specific agent stacks.
3. Keep domain logic outside the core runtime.
4. Use clear contracts: schemas, prompt templates, tool policies, output contracts, evals, and approval rules.
5. Prefer explicit workflows over uncontrolled agent loops.
6. Every agent run must produce traceable artifacts: input, plan, tool calls, evidence, output, cost, errors, and evaluation result.
7. High-risk actions must require human approval.
8. Obsidian is not just a note sink; it is a local-first research and memory workspace.
9. AutoResearcher is a first-class layer for Karpathy-style fixed-budget improvement of measurable domain assets such as agents, prompts, contracts, policies, and eval rubrics.
10. All code must be production-oriented: typed, testable, observable, and Dockerized.

---

## 0.1 Implementation Status Snapshot

This blueprint is both a target architecture and a living record of what has already been built.
As of `2026-06-09`, the repository includes a working backend foundation with tested contracts,
runtime execution, trace persistence abstractions, configurable model providers, Dockerized local
services, and domain-stack examples.

### Completed foundation

```text
FastAPI application shell
Pydantic v2 contract models
YAML-backed domain and tool registries
Domain stacks for research, cybersecurity, productivity, and investor/GTM
Simple planner and runtime execution flow
Governed tool registry, tool policy checks, approval requests, and trace records
Run, step, tool call, artifact, evaluation, approval, document, chunk, embedding, and audit repositories
In-memory repository for local development and tests
SQLAlchemy repository adapter and full initial Alembic schema
Document ingestion, chunking, lexical search, and Qdrant vector store adapter
Artifact inline/external storage threshold behavior with S3/MinIO object writer
Stub model gateway and configurable provider gateways
OpenAI/ChatGPT API, OpenRouter, Claude/Anthropic, Gemini, and Ollama model adapters
Docker Compose services for API, worker, Postgres, Redis, Qdrant, MinIO, Ollama, and Obsidian
AutoResearcher v0.1 planning artifacts
Obsidian Docker service, mounted NeuroAgent vault, and file-backed note write/search adapter
Operational endpoints for storage status, model status, and contract seeding
OpenAPI generation and user test scenarios
```

### Current limitations

```text
API key authentication is implemented and can be enabled with `API_AUTH_ENABLED=true`.
Tenant isolation is enforced on tenant-scoped API routes when API auth is enabled.
Qdrant-backed API RAG search is implemented with repository metadata hydration and lexical fallback.
Obsidian Local REST API plugin automation is not implemented; current enabled mode uses direct vault file writes/search.
Provider gateways are implemented, but live provider smoke tests require user API keys.
Local Ollama model availability depends on the user's hardware and Ollama registry tags.
Workers and queues are scaffolded but not yet the primary execution path.
Cost accounting is estimated and not provider-price accurate.
```

### Architectural direction

The next implementation phases should move the framework from a tested backend foundation toward
a production-grade agent platform:

```text
1. Add Obsidian Local REST API plugin automation if REST semantics are required beyond file-backed vault operations.
2. Move long-running work to Redis-backed worker jobs.
3. Add observability, structured logs, metrics, and trace export.
4. Expand evaluations into benchmarkable domain datasets.
5. Add UI/admin workflows after API behavior is stable.
```

---

## 1. Product Definition

### 1.1 One-line definition

**NeuroAgent Framework is a production-ready operating framework for building governed, domain-specific AI agents with RAG, tool execution, memory, evaluation, and research workflows.**

### 1.2 What this framework is

It is a reusable infrastructure layer for building AI workers that can:

- understand a task,
- select a domain stack,
- retrieve relevant knowledge,
- plan execution,
- call approved tools,
- write structured artifacts,
- store knowledge in Obsidian,
- expose results through API/UI,
- generate audit logs and evaluations.

### 1.3 What this framework is not

It is not:

- a simple prompt library,
- a single chatbot,
- a LangChain wrapper only,
- a pure RAG API,
- a no-control autonomous agent loop,
- an unbounded tool-calling system.

The central product is not the prompt. The central product is:

```text
Agent Contract + Runtime + Domain Stack + Tool Governance + Memory + Evaluation
```

---

## 2. Core Architectural Philosophy

### 2.1 Separation of concerns

The system must be separated into the following layers:

```text
NeuroAgent Framework
│
├── Runtime Layer
├── Prompt & Plan Layer
├── RAG & Knowledge Layer
├── Tool & MCP Layer
├── Domain Stack Layer
├── AutoResearcher Layer
├── Obsidian Memory Layer
├── Evaluation & Governance Layer
├── API Layer
└── Deployment Layer
```

### 2.2 Core principle

The **core runtime** must be domain-agnostic.  
The **domain stack** must be pluggable.

Example:

```text
Core Runtime
  ├── agent execution
  ├── workflow orchestration
  ├── memory handling
  ├── tool registry
  ├── tracing
  ├── evals
  └── governance

Domain Stack
  ├── cybersecurity agents
  ├── research agents
  ├── productivity agents
  ├── investor/GTM agents
  └── custom domain packs
```

### 2.3 Deterministic workflow vs agentic reasoning

Use this rule:

```text
Repeatable infrastructure task → deterministic workflow
Open-ended reasoning task      → agent
Risky external action          → human approval
```

Examples:

| Task | Execution Type |
|---|---|
| Document ingestion | Workflow |
| Chunking and embedding | Workflow |
| Vector search | Workflow/tool |
| Literature research | Agent |
| Hypothesis generation | Agent |
| Sigma rule generation | Agent |
| Production deployment | Human approval |
| Email sending | Human approval |
| Obsidian note creation | Workflow with agent-generated content |

---

## 3. Recommended Technology Stack

### 3.1 Backend

```text
Python 3.12+
FastAPI
Pydantic v2
SQLAlchemy or SQLModel
Alembic
LangGraph or OpenAI Agents SDK
```

### 3.2 Storage

```text
PostgreSQL        → relational metadata, users, tenants, runs, artifacts
Qdrant            → primary vector search backend
pgvector          → optional future vector adapter
Redis             → cache, job status, queue broker
MinIO/S3          → raw files, large artifacts, exports
```

Storage rules:

```text
PostgreSQL is the metadata source of truth.
Qdrant stores vectors and retrieval payloads, not canonical document metadata.
Small artifacts may be stored inline in PostgreSQL.
Large artifacts must be written to S3/MinIO and referenced by storage_uri.
The in-memory repository is allowed only for development and tests.
Production must fail fast when DATABASE_URL is missing.
Every tenant-scoped record must carry tenant_id.
```

### 3.3 Agent / orchestration

Initial recommendation:

```text
MVP/current: FastAPI + internal deterministic workflow runtime + configurable model gateway
Optional later: LangGraph adapter for long-running/resumable graph workflows
Optional: OpenAI Agents SDK adapter
Later: internal graph runtime if needed
```

Reason:

- LangGraph is useful for long-running, stateful, resumable agent workflows.
- OpenAI Agents SDK can be added as a provider/runtime adapter.
- The internal architecture must not depend entirely on one vendor.

### 3.3.1 Model gateway

The model layer must be provider-agnostic. The runtime receives a `ModelGateway` interface and
does not call provider SDKs directly.

Supported provider families:

```text
stub        → deterministic local test/dev output
openai      → OpenAI/ChatGPT API through Responses API
openrouter  → OpenAI-compatible chat completions
anthropic   → Claude Messages API
gemini      → Gemini generateContent API
ollama      → local models through Ollama OpenAI-compatible API
```

Configuration is environment-driven:

```text
MODEL_PROVIDER=stub|openai|openrouter|anthropic|gemini|ollama
DEFAULT_MODEL
OPENAI_API_KEY
OPENROUTER_API_KEY
ANTHROPIC_API_KEY
GEMINI_API_KEY
OLLAMA_BASE_URL
OLLAMA_MODEL
```

Local Ollama model choices should be configurable through environment aliases, including
DeepSeek-R1, Kimi K2.6, GLM-5.1, Qwen 3.5, Qwen2.5-Coder, and Gemma 4. The framework must not
assume those model tags are always available in every Ollama environment; aliases must be
overridable.

### 3.4 RAG

```text
Document loaders
Chunking engine
Embedding provider interface
Vector database adapter
Hybrid search adapter
Reranker adapter
Citation/evidence engine
```

RAG implementation rules:

```text
Document metadata and chunks are persisted in PostgreSQL.
Vector payloads must include tenant_id, domain_id, document_id, chunk_id, source_uri, title, hash, and embedding_model.
Retrieval must filter by tenant_id and domain_id before returning evidence.
Search responses must include cited chunks, scores, source metadata, and confidence.
The lexical in-memory retriever is a development fallback, not the production retrieval path.
```

### 3.5 Tooling

```text
Internal tools
MCP tools
Obsidian tools
Web/search tools
GitHub tools
File tools
Domain tools
```

### 3.6 Observability

```text
Structured logging
OpenTelemetry-compatible tracing
Agent run trace table
Tool call trace table
Cost/token usage table
Error table
Evaluation table
```

### 3.7 Deployment

```text
Docker Compose for local/MVP
Kubernetes later
GitHub Actions CI/CD
.env.example
Makefile
Pre-commit hooks
```

---

## 4. High-Level System Architecture

```text
Client / UI / API Consumer
        │
        ▼
FastAPI Gateway
        │
        ├── Auth / Tenant Middleware
        ├── Request Validation
        ├── Rate Limit
        └── API Versioning
        │
        ▼
Agent Runtime
        │
        ├── Intent Router
        ├── Domain Stack Resolver
        ├── Agent Contract Loader
        ├── Plan Generator
        ├── Workflow Executor
        ├── Tool Executor
        ├── Human Approval Gate
        └── Artifact Writer
        │
        ├──────────────┬──────────────┬──────────────┐
        ▼              ▼              ▼              ▼
RAG Layer       Tool Registry   Obsidian Layer   Eval/Governance
        │              │              │              │
        ▼              ▼              ▼              ▼
Vector DB       MCP/Tools       Markdown Vault   Trace/Eval DB
        │              │              │              │
        └──────────────┴──────────────┴──────────────┘
                         │
                         ▼
                  Final Response
                  Artifacts
                  Audit Trail
```

---

## 5. Repository Structure

Codex should create the initial repository using this structure:

```text
neuroagent-framework/
│
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Makefile
├── CONTRIBUTING.md
│
├── docs/
│   ├── architecture.md
│   ├── agent-contract.md
│   ├── domain-stack.md
│   ├── obsidian-layer.md
│   ├── autoresearcher-layer.md
│   ├── evals.md
│   ├── security.md
│   └── roadmap.md
│
├── app/
│   ├── main.py
│   ├── settings.py
│   ├── dependencies.py
│   │
│   ├── api/
│   │   ├── routes_agents.py
│   │   ├── routes_runs.py
│   │   ├── routes_documents.py
│   │   ├── routes_tools.py
│   │   ├── routes_domains.py
│   │   ├── routes_obsidian.py
│   │   └── routes_evals.py
│   │
│   ├── core/
│   │   ├── runtime.py
│   │   ├── orchestrator.py
│   │   ├── intent_router.py
│   │   ├── planner.py
│   │   ├── executor.py
│   │   ├── approvals.py
│   │   ├── artifacts.py
│   │   └── errors.py
│   │
│   ├── contracts/
│   │   ├── agent_contract.py
│   │   ├── tool_contract.py
│   │   ├── workflow_contract.py
│   │   ├── domain_contract.py
│   │   ├── eval_contract.py
│   │   └── artifact_contract.py
│   │
│   ├── prompts/
│   │   ├── registry.py
│   │   ├── renderer.py
│   │   ├── validators.py
│   │   └── templates/
│   │       ├── planner.md
│   │       ├── critic.md
│   │       ├── researcher.md
│   │       └── summarizer.md
│   │
│   ├── rag/
│   │   ├── ingestion.py
│   │   ├── chunking.py
│   │   ├── embeddings.py
│   │   ├── vectorstore.py
│   │   ├── retriever.py
│   │   ├── reranker.py
│   │   ├── citations.py
│   │   └── schemas.py
│   │
│   ├── tools/
│   │   ├── registry.py
│   │   ├── executor.py
│   │   ├── policy.py
│   │   ├── base.py
│   │   ├── mcp_adapter.py
│   │   ├── web_search.py
│   │   ├── file_tools.py
│   │   ├── github_tools.py
│   │   └── domain_tools/
│   │       ├── sigma.py
│   │       ├── yara.py
│   │       └── mitre.py
│   │
│   ├── memory/
│   │   ├── short_term.py
│   │   ├── long_term.py
│   │   ├── state_store.py
│   │   └── schemas.py
│   │
│   ├── obsidian/
│   │   ├── client.py
│   │   ├── vault.py
│   │   ├── templates.py
│   │   ├── note_writer.py
│   │   ├── note_reader.py
│   │   └── schemas.py
│   │
│   ├── autoresearcher/
│   │   ├── pipeline.py
│   │   └── schemas.py
│   │
│   ├── domains/
│   │   ├── registry.py
│   │   ├── base.py
│   │   │
│   │   ├── research/
│   │   │   ├── domain.yaml
│   │   │   ├── agents/
│   │   │   │   ├── literature_researcher.yaml
│   │   │   │   ├── hypothesis_generator.yaml
│   │   │   │   └── research_critic.yaml
│   │   │   ├── tools.yaml
│   │   │   ├── evals.yaml
│   │   │   └── prompts/
│   │   │
│   │   ├── cybersecurity/
│   │   │   ├── domain.yaml
│   │   │   ├── agents/
│   │   │   │   ├── threat_researcher.yaml
│   │   │   │   ├── sigma_rule_agent.yaml
│   │   │   │   ├── yara_rule_agent.yaml
│   │   │   │   └── detection_critic.yaml
│   │   │   ├── tools.yaml
│   │   │   ├── evals.yaml
│   │   │   └── prompts/
│   │   │
│   │   ├── productivity/
│   │   │   ├── domain.yaml
│   │   │   ├── agents/
│   │   │   │   ├── focus_coach.yaml
│   │   │   │   ├── planning_agent.yaml
│   │   │   │   └── weekly_review_agent.yaml
│   │   │   └── prompts/
│   │   │
│   │   └── investor_gtm/
│   │       ├── domain.yaml
│   │       ├── agents/
│   │       │   ├── investor_researcher.yaml
│   │       │   ├── outreach_writer.yaml
│   │       │   └── pitch_critic.yaml
│   │       └── prompts/
│   │
│   ├── evals/
│   │   ├── runner.py
│   │   ├── validators.py
│   │   ├── rubric.py
│   │   ├── datasets/
│   │   └── reports.py
│   │
│   ├── governance/
│   │   ├── guardrails.py
│   │   ├── policies.py
│   │   ├── permissions.py
│   │   ├── audit.py
│   │   └── red_team.py
│   │
│   ├── db/
│   │   ├── session.py
│   │   ├── models.py
│   │   ├── repositories.py
│   │   └── migrations/
│   │
│   └── workers/
│       ├── queue.py
│       ├── tasks.py
│       └── scheduler.py
│
├── tests/
│   ├── test_agent_contracts.py
│   ├── test_tool_policy.py
│   ├── test_rag_pipeline.py
│   ├── test_obsidian_adapter.py
│   ├── test_autoresearcher_pipeline.py
│   └── test_api_health.py
│
├── examples/
│   ├── research_agent_run.json
│   ├── cybersecurity_sigma_request.json
│   ├── productivity_weekly_review.json
│   └── obsidian_note_output.md
│
└── scripts/
    ├── init_db.py
    ├── seed_domains.py
    ├── ingest_docs.py
    └── run_eval_suite.py
```

---

## 6. Core Data Model

### 6.1 Required database entities

Codex should implement these models first:

```text
Tenant
User
DomainStack
AgentDefinition
PromptTemplate
ToolDefinition
ToolPolicy
AgentRun
AgentStep
ToolCall
Artifact
Document
DocumentChunk
EmbeddingRecord
EvaluationRun
EvaluationResult
ApprovalRequest
AuditLog
ObsidianNoteRecord
```

### 6.2 Suggested fields

#### AgentRun

```text
id
tenant_id
user_id
domain_id
agent_id
status
input_payload
resolved_plan
final_output
error_message
token_usage
cost_estimate
started_at
completed_at
created_at
updated_at
```

#### AgentStep

```text
id
run_id
step_index
step_type
name
input_payload
output_payload
status
error_message
started_at
completed_at
```

#### ToolCall

```text
id
run_id
step_id
tool_name
tool_version
input_payload
output_payload
risk_level
approval_required
approval_status
latency_ms
error_message
created_at
```

#### Artifact

```text
id
run_id
artifact_type
name
content
storage_uri
metadata
created_at
```

#### EvaluationResult

```text
id
run_id
eval_name
passed
score
rubric
findings
created_at
```

---

## 7. Agent Contract

Each agent must be defined through a contract file.

Example:

```yaml
agent_id: cybersecurity.sigma_rule_agent
name: Sigma Rule Agent
version: 0.1.0
domain: cybersecurity
risk_level: medium

role: >
  You are a detection engineering agent specialized in Sigma rules,
  Windows/Linux telemetry, log sources, and behavior-based threat detection.

goal: >
  Convert threat behavior descriptions into explainable Sigma detection logic
  with evidence, assumptions, false-positive analysis, and validation notes.

input_schema:
  type: object
  required:
    - threat_description
    - target_platform
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
  required:
    - summary
    - sigma_rule
    - evidence
    - false_positive_analysis
    - confidence_score
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

forbidden_tools:
  - shell.execute
  - production.deploy_rule

human_approval_required_for:
  - production.deploy_rule
  - external_email.send
  - customer_report.publish

evaluation:
  - output_schema_valid
  - evidence_required
  - no_uncited_claims
  - sigma_yaml_valid
  - false_positive_analysis_present
```

---

## 8. Domain Stack Contract

A domain stack is a packaged domain-specific capability layer.

### 8.1 Domain stack contents

```text
Domain metadata
Domain agents
Domain prompts
Domain tools
Domain schemas
Domain evals
Domain policies
Domain knowledge sources
Domain examples
```

### 8.2 Domain contract example

```yaml
domain_id: cybersecurity
name: Cybersecurity Domain Stack
version: 0.1.0
status: experimental

supported_tasks:
  - threat_research
  - sigma_rule_generation
  - yara_rule_generation
  - log_analysis
  - incident_report
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

---

## 9. Prompt & Plan Layer

### 9.1 Purpose

The Prompt & Plan Layer must not be a simple prompt directory. It must manage:

```text
Prompt templates
Agent instructions
Planning templates
Output contracts
Tool-use rules
Risk rules
Evaluation rubrics
Version history
```

### 9.2 Planner prompt responsibilities

The planner must produce:

```text
intent
domain_stack
selected_agent_or_workflow
required_tools
execution_steps
expected_artifacts
approval_points
success_criteria
```

### 9.3 Plan schema

```json
{
  "intent": "research",
  "domain": "cybersecurity",
  "agent_id": "cybersecurity.threat_researcher",
  "steps": [
    {
      "step_id": "retrieve_background",
      "type": "tool_call",
      "tool": "rag.search",
      "input": {}
    },
    {
      "step_id": "generate_findings",
      "type": "agent_reasoning",
      "input": {}
    },
    {
      "step_id": "write_obsidian_note",
      "type": "tool_call",
      "tool": "obsidian.write_note",
      "approval_required": false
    }
  ],
  "approval_points": [],
  "expected_artifacts": [
    "summary.md",
    "evidence.json",
    "obsidian_note.md"
  ]
}
```

---

## 10. RAG & Knowledge Layer

### 10.1 Pipeline

```text
Document upload/import
  ↓
Document normalization
  ↓
Chunking
  ↓
Metadata extraction
  ↓
Embedding generation
  ↓
Vector storage
  ↓
Retrieval
  ↓
Reranking
  ↓
Evidence packaging
  ↓
Cited answer generation
```

### 10.2 Document metadata

Every chunk must include:

```text
document_id
chunk_id
tenant_id
domain_id
source_type
source_uri
title
author
created_at
page_number
section
hash
embedding_model
```

### 10.3 Retrieval policy

The retriever must return:

```text
chunk text
score
source metadata
citation id
confidence
```

### 10.4 Evidence-first output

Agents must not produce research claims without evidence when the task requires factual grounding.

Output should include:

```json
{
  "claim": "...",
  "evidence": [
    {
      "source_id": "doc_123",
      "chunk_id": "chunk_9",
      "quote_or_summary": "...",
      "confidence": 0.82
    }
  ]
}
```

---

## 11. Tool & MCP Layer

### 11.1 Tool registry

Every tool must have a contract:

```yaml
tool_id: obsidian.write_note
name: Obsidian Write Note
version: 0.1.0
risk_level: low
requires_approval: false
input_schema: {}
output_schema: {}
timeout_seconds: 30
allowed_domains:
  - research
  - cybersecurity
  - productivity
```

### 11.2 Tool risk levels

```text
low       → read-only or local note writing
medium    → external API calls, customer-visible drafts
high      → production changes, code execution, email sending, deletion
critical  → irreversible or security-sensitive actions
```

### 11.3 Approval rules

Require approval for:

```text
Sending emails
Posting publicly
Deploying detection rules
Deleting files
Running shell commands
Changing infrastructure
Calling unknown MCP tools
Accessing sensitive data
```

### 11.4 MCP policy

MCP should be supported through an adapter, but never blindly trusted.

Rules:

```text
MCP tools must be allowlisted.
MCP tool descriptions must be cached and reviewed.
MCP calls must be traced.
Unknown MCP tools are blocked by default.
High-risk MCP tools require approval.
MCP servers must be tenant-scoped.
```

---

## 12. Obsidian Memory Layer

### 12.1 Purpose

Obsidian acts as:

```text
Research workspace
Local-first memory
Agent artifact archive
Decision log
Knowledge graph
Human-readable audit layer
```

### 12.2 Recommended vault structure

```text
NeuroAgentVault/
│
├── 00_Inbox/
├── 01_Research/
│   ├── Literature/
│   ├── Hypotheses/
│   ├── Experiments/
│   └── Paper_Drafts/
│
├── 02_Domains/
│   ├── Cybersecurity/
│   ├── Productivity/
│   ├── Blockchain/
│   └── Investor_GTM/
│
├── 03_Agent_Runs/
│   ├── Daily/
│   ├── Weekly/
│   └── By_Domain/
│
├── 04_Decisions/
├── 05_Evaluations/
├── 06_Meetings/
├── 07_Artifacts/
└── 99_Archive/
```

### 12.3 Note template: Agent run

```markdown
---
type: agent_run
run_id: {{run_id}}
agent_id: {{agent_id}}
domain: {{domain}}
date: {{date}}
status: {{status}}
confidence: {{confidence}}
tags:
  - neuroagent
  - agent-run
  - {{domain}}
---

# Agent Run: {{agent_id}}

## User Request

{{user_request}}

## Execution Plan

{{execution_plan}}

## Key Findings

{{findings}}

## Evidence

{{evidence}}

## Output Artifacts

{{artifacts}}

## Open Questions

{{open_questions}}

## Next Actions

{{next_actions}}

## Evaluation

{{evaluation_summary}}
```

### 12.4 Note template: Research hypothesis

```markdown
---
type: research_hypothesis
domain: {{domain}}
status: draft
confidence: {{confidence}}
tags:
  - research
  - hypothesis
  - {{domain}}
---

# {{title}}

## Problem

{{problem}}

## Hypothesis

{{hypothesis}}

## Why it matters

{{importance}}

## Supporting Evidence

{{evidence}}

## Counterarguments

{{counterarguments}}

## Experiment Plan

{{experiment_plan}}

## Risks

{{risks}}

## Next Steps

{{next_steps}}
```

---

## 13. AutoResearcher Layer

### 13.1 Purpose

AutoResearcher is the NeuroAgent adaptation of Karpathy's `autoresearch` pattern.

It is **not** a literature review or paper-writing layer.

In NeuroAgent, AutoResearcher exists to improve measurable domain-stack assets:

```text
Agent contracts
Prompt templates
Domain contracts
Tool policies
Eval rubrics
Output schemas
Approval rules
```

The core pattern is:

```text
Constrained editable target
  ↓
program.md instructions
  ↓
fixed experiment budget
  ↓
measurable evaluation metric
  ↓
keep/discard decision
```

It must support:

```text
Domain asset selection
Measurement definition
program.md generation
Fixed-budget improvement loop planning
Eval suite execution
Metric comparison
Patch keep/discard recommendation
Improvement backlog generation
```

### 13.2 Pipeline

```text
Domain Stack
  ↓
Measurable Asset Selection
  ↓
Baseline Metric Snapshot
  ↓
Autoresearch program.md Generation
  ↓
Fixed-Budget Agent Experiment
  ↓
Contract / Prompt / Policy / Eval Patch
  ↓
Eval Suite Run
  ↓
Metric Comparison
  ↓
Keep / Discard Decision
```

### 13.3 Editable target types

```text
agent_contract
prompt_template
domain_contract
tool_policy
eval_rubric
```

### 13.4 Output artifacts

```text
program.md
experiment_plan.json
measurement_rubric.json
improvement_backlog.md
metric_comparison.json
keep_discard_decision.md
```

### 13.5 First target improvement use cases

```text
Improve Sigma Rule Agent output contract quality
Improve cybersecurity eval rubric coverage
Improve research domain prompt measurability
Improve productivity domain privacy policy checks
Improve investor/GTM source-citation requirements
Improve domain-stack acceptance criteria
```

---

## 14. Domain Stacks for v0.1

### 14.1 Research Domain Stack

Agents:

```text
Literature Researcher
Hypothesis Generator
Research Critic
Experiment Planner
Paper Outline Agent
```

Tools:

```text
rag.search
web.search
obsidian.write_note
citation.verify
file.write_artifact
```

Example task:

```text
Research Sigma rules as behavioral vectors and produce a structured research note with evidence, counterarguments, and experiment plan.
```

### 14.2 Cybersecurity Domain Stack

Agents:

```text
Threat Researcher
Sigma Rule Agent
YARA Rule Agent
Detection Critic
Incident Report Agent
False Positive Reviewer
```

Tools:

```text
sigma.validate_yaml
yara.validate_rule
mitre.lookup
rag.search
obsidian.write_note
file.write_artifact
```

Example task:

```text
Generate a Sigma detection strategy for suspicious PowerShell execution and write a detection engineering note.
```

### 14.3 Productivity Domain Stack

Agents:

```text
Focus Coach Agent
Planning Agent
Weekly Review Agent
Motivation Pattern Agent
Goal Alignment Agent
```

Tools:

```text
productivity.metrics_search
calendar.read
obsidian.write_note
report.generate
```

Example task:

```text
Analyze weekly focus patterns and generate an improvement plan.
```

### 14.4 Investor/GTM Domain Stack

Agents:

```text
Investor Researcher
Investor Fit Scorer
Outreach Writer
Pitch Critic
Market Research Agent
Competitor Intelligence Agent
```

Tools:

```text
web.search
company.lookup
obsidian.write_note
crm.write_lead
file.write_artifact
```

Example task:

```text
Find investor-fit signals and generate a meeting brief for Neurobytes.
```

---

## 15. API Design

### 15.1 Health

```http
GET /health
```

### 15.2 Domains

```http
GET /domains
GET /domains/{domain_id}
POST /domains/{domain_id}/reload
```

### 15.3 Agents

```http
GET /agents
GET /agents/{agent_id}
POST /agents/{agent_id}/run
```

### 15.4 Runs

```http
GET /runs
GET /runs/{run_id}
GET /runs/{run_id}/steps
GET /runs/{run_id}/tool-calls
GET /runs/{run_id}/artifacts
POST /runs/{run_id}/cancel
```

### 15.5 Documents / RAG

```http
POST /documents/upload
POST /documents/ingest
GET /documents
GET /documents/{document_id}
POST /rag/search
```

### 15.6 Tools

```http
GET /tools
GET /tools/{tool_id}
POST /tools/{tool_id}/test
```

### 15.7 Obsidian

```http
POST /obsidian/notes
GET /obsidian/notes/search
POST /obsidian/agent-run-note
```

### 15.8 Evaluations

```http
POST /evals/run/{run_id}
GET /evals/{run_id}
GET /evals/reports
```

### 15.9 Approvals

```http
GET /approvals/pending
POST /approvals/{approval_id}/approve
POST /approvals/{approval_id}/reject
```

---

## 16. Environment Variables

Create `.env.example` with:

```bash
APP_NAME=neuroagent-framework
APP_ENV=development
APP_DEBUG=true

API_HOST=0.0.0.0
API_PORT=8000

DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/neuroagent
REDIS_URL=redis://redis:6379/0

VECTOR_BACKEND=qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=
PGVECTOR_DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/neuroagent

OPENAI_API_KEY=
ANTHROPIC_API_KEY=
DEFAULT_MODEL=gpt-4.1-mini
DEFAULT_EMBEDDING_MODEL=text-embedding-3-small

OBSIDIAN_ENABLED=false
OBSIDIAN_BASE_URL=http://127.0.0.1:27123
OBSIDIAN_API_KEY=
OBSIDIAN_VAULT_NAME=NeuroAgentVault

ENABLE_MCP=false
MCP_CONFIG_PATH=./mcp.config.json

S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minio
S3_SECRET_KEY=minio123
S3_BUCKET=neuroagent-artifacts

LOG_LEVEL=INFO
ENABLE_TRACING=true
```

---

## 17. Docker Compose Services

Initial `docker-compose.yml` should include:

```text
api
worker
postgres
redis
qdrant
minio
```

Optional later:

```text
frontend
prometheus
grafana
otel-collector
```

---

## 18. Evaluation & Governance

### 18.1 Minimum evaluation checks

Every agent run should be evaluated with:

```text
output_schema_valid
no_empty_answer
evidence_required_if_research_task
tool_policy_respected
no_forbidden_tool_called
approval_rules_respected
obsidian_note_written_if_required
```

### 18.2 Domain-specific checks

Cybersecurity:

```text
sigma_yaml_valid
yara_rule_valid
mitre_mapping_present
false_positive_analysis_present
no_production_deploy_without_approval
```

Research:

```text
claims_have_evidence
counterarguments_present
limitations_present
experiment_plan_present
citations_verified
```

Productivity:

```text
no_surveillance_language
user_agency_preserved
recommendations_actionable
privacy_boundary_respected
```

Investor/GTM:

```text
no_fake_investor_claims
source_links_required
message_is_concise
fit_score_explained
```

### 18.3 Guardrail policy

Agents must:

```text
State uncertainty.
Never invent citations.
Never claim tool execution if it failed.
Never perform destructive actions without approval.
Never expose secrets.
Never write credentials to Obsidian.
Never send external messages without approval.
Never run shell commands unless allowlisted.
```

---

## 19. Development Roadmap

The roadmap below reflects the implementation state as of `2026-06-09`.

Legend:

```text
Done        → implemented and covered by tests or API smoke checks
In Progress → partially implemented, needs production wiring or live integration
Planned     → not yet implemented
```

### Phase 0 — Skeleton — Done

Codex tasks:

```text
Create repository structure.
Create FastAPI app.
Create settings loader.
Create health endpoint.
Create Docker Compose with Postgres, Redis, Qdrant, MinIO.
Create basic database models.
Create Makefile.
Create initial tests.
```

Acceptance criteria:

```text
make dev starts the stack.
GET /health returns ok.
Tests pass.
.env.example exists.
Database migrations run.
```

Status notes:

```text
FastAPI app, settings, Docker Compose, Makefile, health endpoint, tests, and initial structure exist.
Docker Compose now includes API, worker, Postgres, Redis, Qdrant, MinIO, and Ollama.
```

### Phase 1 — Contracts & Registry — Done

Codex tasks:

```text
Implement AgentContract Pydantic model.
Implement ToolContract Pydantic model.
Implement DomainContract Pydantic model.
Implement registry loaders for YAML files.
Add validation tests.
Seed research and cybersecurity domains.
```

Acceptance criteria:

```text
GET /domains returns loaded domains.
GET /agents returns loaded agents.
Invalid YAML contracts fail validation.
```

Status notes:

```text
Agent, tool, domain, workflow, eval, and artifact contracts exist.
YAML registries load research, cybersecurity, productivity, and investor/GTM stacks.
```

### Phase 2 — Basic Runtime — Done

Codex tasks:

```text
Implement agent run creation.
Implement simple planner.
Implement step executor.
Implement artifact writer.
Implement run trace persistence.
```

Acceptance criteria:

```text
POST /agents/{agent_id}/run creates a run.
Run has steps.
Run has final output.
Run trace is persisted.
```

Status notes:

```text
Runtime validates input, plans steps, executes reasoning/tool steps, writes artifacts, evaluates runs, and rehydrates trace collections.
```

### Phase 3 — Tool Registry — Done

Codex tasks:

```text
Implement tool registry.
Implement tool policy checker.
Implement low-risk tools.
Implement approval gate for high-risk tools.
Add tool call trace logging.
```

Acceptance criteria:

```text
Allowed tools execute.
Forbidden tools are blocked.
High-risk tools create approval requests.
Tool calls are logged.
```

Status notes:

```text
Tool contracts, tool policy, approval gate, tool call traces, and low-risk/stub tools exist.
```

### Phase 4 — Persistence Layer — Substantially Done

Codex tasks:

```text
Implement repository protocol.
Implement in-memory repository for tests/development.
Implement SQLAlchemy repository for Postgres.
Implement full initial Alembic schema.
Persist runs, steps, tool calls, artifacts, evals, approvals, documents, chunks, embeddings, audit logs, and Obsidian records.
Add storage status endpoint.
Add contract seeding endpoint.
```

Acceptance criteria:

```text
Development without DATABASE_URL uses memory repository.
Production without DATABASE_URL fails fast.
Postgres migration creates all required tables and indexes.
DB-backed run survives API restart.
Approvals and RAG metadata persist across repository calls.
```

Status notes:

```text
Repository protocol, memory repository, SQLAlchemy repository, and initial schema are implemented.
Storage status and contract seeding endpoints exist.
Live Postgres upgrade/downgrade and restart scenarios still need environment-backed validation.
```

### Phase 5 — Model Gateway — Done

Codex tasks:

```text
Keep deterministic stub gateway for tests.
Add provider factory selected by MODEL_PROVIDER.
Implement OpenAI/ChatGPT API gateway.
Implement OpenRouter gateway.
Implement Claude/Anthropic gateway.
Implement Gemini gateway.
Implement local Ollama gateway.
Add model status endpoint.
Add Docker Ollama service and optional model pull profile.
```

Acceptance criteria:

```text
Default tests run without API keys.
Provider payloads are constructed correctly.
Missing API keys fail fast.
Model output is parsed as JSON and validated against agent output schema.
Local Ollama can be selected through env.
```

Status notes:

```text
Provider adapters, factory, model status endpoint, Ollama service, and provider unit tests are implemented.
Live provider smoke tests require user API keys and local model availability.
```

### Phase 6 — RAG Layer — Substantially Done

Codex tasks:

```text
Implement document ingestion.
Implement chunking.
Implement embedding provider abstraction.
Implement Qdrant adapter.
Implement RAG search endpoint.
Implement citation package format.
```

Acceptance criteria:

```text
Document can be ingested.
Chunks are stored.
Embeddings are stored.
RAG search returns cited chunks.
```

Status notes:

```text
Document ingestion, chunking, repository-backed metadata, lexical search fallback, Qdrant adapter,
ingest-time vector indexing, embedding records, and `/rag/search` vector retrieval with repository
metadata hydration are implemented.
Live Qdrant smoke tests still require an environment-backed service.
```

### Phase 7 — Obsidian Layer — Substantially Done

Codex tasks:

```text
Implement Obsidian client.
Implement write note tool.
Implement search note tool.
Implement agent run note template.
Implement research note template.
```

Acceptance criteria:

```text
Agent can write a Markdown note to Obsidian.
Note contains frontmatter.
Note links run_id and agent_id.
```

Status notes:

```text
Docker Compose runs Obsidian as a separate service with a mounted NeuroAgent vault.
Disabled mode returns deterministic note payloads.
Enabled mode writes Markdown files directly to the configured vault and searches Markdown notes.
Obsidian Local REST API plugin automation remains optional future work.
```

### Phase 8 — AutoResearcher v0.1 — In Progress

Codex tasks:

```text
Implement Karpathy-style AutoResearcher domain improvement planner.
Implement measurable asset target schemas.
Implement program.md generation.
Implement measurement rubric generation.
Implement improvement backlog generation.
Implement keep/discard decision model.
```

Acceptance criteria:

```text
AutoResearcher produces program.md for a target domain.
Artifacts include experiment_plan.json, measurement_rubric.json, improvement_backlog.md.
The output identifies editable assets, fixed context, primary metric, and acceptance rule.
It is used to improve agents, prompts, contracts, policies, and eval rubrics.
```

Status notes:

```text
AutoResearcher planning artifacts exist.
Execution of fixed-budget improvement loops, metric comparison, and keep/discard persistence need expansion.
```

### Phase 9 — Cybersecurity Domain v0.1 — In Progress

Codex tasks:

```text
Implement Sigma YAML validation tool.
Implement MITRE lookup adapter stub.
Implement Sigma Rule Agent contract.
Implement Detection Critic Agent contract.
Implement cybersecurity evals.
```

Acceptance criteria:

```text
Sigma request returns valid YAML.
False-positive analysis is present.
Eval result is generated.
```

Status notes:

```text
Cybersecurity contracts, Sigma/YARA/MITRE tool stubs, and eval scaffolding exist.
Production-grade validation, MITRE enrichment, and benchmark datasets remain to be expanded.
```

### Phase 10 — Artifact Object Storage — Done

Codex tasks:

```text
Implement S3/MinIO object writer.
Serialize large artifacts to object storage.
Persist storage_uri and content hash in Postgres.
Add object read/download endpoint where appropriate.
Add tests for inline vs external artifact behavior.
```

Acceptance criteria:

```text
Small artifacts remain inline.
Large artifacts are written to MinIO/S3.
Artifacts survive API restart.
Missing object storage config produces explicit errors in production.
```

Status notes:

```text
Artifact storage helper serializes content, calculates hash/size metadata, writes large artifacts
through an S3-compatible object storage adapter, and persists storage_uri with inline content cleared.
In-memory development mode keeps a deterministic memory:// fallback.
```

### Phase 11 — Authentication & Tenant Enforcement — Substantially Done

Codex tasks:

```text
Add API key authentication strategy.
Resolve tenant from API key.
Enforce tenant filters in repository-backed API endpoints.
Add user and service-account model support later if JWT/OIDC is needed.
Validate tenant API keys and admin API keys.
Add authorization policies for admin endpoints.
```

Acceptance criteria:

```text
Tenant A cannot read Tenant B runs, documents, approvals, artifacts, or audit logs.
Admin endpoints require admin authorization.
Unauthenticated access is limited to health and public documentation endpoints.
```

Status notes:

```text
API key auth is implemented through X-API-Key.
API_KEYS uses key:tenant_id entries.
ADMIN_API_KEYS grants admin access.
Tenant-scoped run, document, RAG, approval, eval, and admin seed routes enforce tenant/admin access.
Auth remains disabled by default for local development and tests.
```

### Phase 12 — Worker Execution & Queues — Planned

Codex tasks:

```text
Move long-running agent runs, ingestion jobs, evals, and AutoResearcher experiments to Redis-backed workers.
Add job status endpoints.
Add retry and timeout policies.
Persist job lifecycle events in audit logs.
```

Acceptance criteria:

```text
API can enqueue long-running work.
Client can poll job status.
Failed jobs preserve trace and error context.
Workers can be restarted without losing persisted state.
```

### Phase 13 — Observability & Cost Governance — Planned

Codex tasks:

```text
Add structured logs.
Add OpenTelemetry-compatible trace hooks.
Add provider latency metrics.
Add cost/token usage aggregation.
Add red-team and policy event reporting.
```

Acceptance criteria:

```text
Every run has trace IDs across API, runtime, tools, model calls, and storage.
Operators can inspect cost and token usage by tenant, domain, model, and agent.
Policy blocks and approvals are auditable.
```

### Phase 14 — Production Hardening — Planned

Codex tasks:

```text
Add rate limiting.
Add error handling.
Add CI pipeline.
Add migration tests against a real database.
Add backup/restore guidance.
Add deployment profiles for local, staging, and production.
Add security review for secrets, tools, MCP, and Obsidian writes.
```

Acceptance criteria:

```text
CI passes.
API requires auth except /health.
Tenant data is isolated.
Trace exists for each run.
```

---

## 20. Initial Codex Implementation Prompts

Use these prompts sequentially with Codex.

### Prompt 1 — Create skeleton

```text
Create the initial Python FastAPI repository for NeuroAgent Framework using the architecture in neuroagent_framework_infrastructure.md. Implement the repository structure, pyproject.toml, .env.example, Docker Compose with api/postgres/redis/qdrant/minio, FastAPI app, settings loader, /health endpoint, Makefile, and basic tests. Do not implement agent logic yet. Keep code typed and clean.
```

### Prompt 2 — Implement contracts

```text
Implement Pydantic v2 contracts for AgentContract, ToolContract, DomainContract, WorkflowContract, EvalContract, and ArtifactContract. Add YAML registry loaders under app/domains/registry.py and app/tools/registry.py. Add tests that validate correct and incorrect YAML files. Seed the research and cybersecurity domain stacks with minimal YAML examples.
```

### Prompt 3 — Implement basic runtime

```text
Implement the first version of the agent runtime. It should load an agent contract, validate input, create an AgentRun, create an execution plan, execute simple reasoning steps through a model gateway stub, persist run steps, and return a final structured output. Do not add external tools yet. Add tests for run lifecycle.
```

### Prompt 4 — Implement tool governance

```text
Implement ToolRegistry, ToolExecutor, and ToolPolicy. Tools must have risk levels and approval rules. Add a local echo tool, file artifact write tool, and obsidian.write_note stub. Forbidden tools must be blocked. High-risk tools must create ApprovalRequest records instead of executing directly.
```

### Prompt 5 — Implement RAG v0.1

```text
Implement document ingestion, chunking, embedding provider interface, Qdrant vector store adapter, and /rag/search endpoint. Use a mock embedding provider for tests. Return evidence objects with chunk_id, source metadata, score, and citation_id.
```

### Prompt 6 — Implement Obsidian adapter

```text
Implement the Obsidian client for local REST API. Add note writing with Markdown frontmatter, note search, and agent run note templates. Ensure Obsidian can be disabled through OBSIDIAN_ENABLED=false. Add tests with mocked HTTP calls.
```

### Prompt 7 — Implement AutoResearcher v0.1

```text
Implement Karpathy-style AutoResearcher support for NeuroAgent domain-stack improvement. It should generate program.md instructions, fixed-budget experiment plans, measurement rubrics, and improvement backlog artifacts for measurable assets such as agent contracts, prompt templates, domain contracts, tool policies, and eval rubrics.
```

### Prompt 8 — Implement cybersecurity Sigma domain

```text
Implement the cybersecurity domain stack v0.1. Add Sigma Rule Agent, Threat Researcher, Detection Critic, Sigma YAML validation tool, MITRE lookup stub, and cybersecurity evals. The Sigma agent must return summary, sigma_rule, evidence, false_positive_analysis, confidence_score, and open_questions.
```

---

## 21. First Demo Scenario

Use this as the first end-to-end demo:

```text
Task:
Improve the Cybersecurity Domain Stack by tightening the Sigma Rule Agent contract, prompt, tool policy, and eval rubric using a fixed-budget AutoResearcher improvement loop.

Expected flow:
1. API receives request.
2. Domain resolver selects cybersecurity.
3. AutoResearcher selects measurable assets.
4. AutoResearcher generates program.md.
5. A fixed-budget agent experiment proposes changes.
6. Contract validation and domain evals run.
7. Metrics are compared against baseline.
8. Keep/discard decision is produced.
9. Artifacts are stored and optionally mirrored into Obsidian.
10. API returns summary, metrics, and artifact list.
```

Expected artifacts:

```text
program.md
experiment_plan.json
measurement_rubric.json
improvement_backlog.md
metric_comparison.json
keep_discard_decision.md
run_trace.json
eval_report.json
```

---

## 22. Commercial Packaging

### 22.1 Open core package

```text
Core runtime
Basic RAG
Tool registry
Local domains
Obsidian adapter
Basic evals
```

### 22.2 Paid/pro package

```text
Advanced domain stacks
Team/tenant support
Advanced observability
Eval dashboards
Human approval UI
GitHub/Slack/Google Drive connectors
Cybersecurity pack
Investor/GTM pack
Productivity analytics pack
```

### 22.3 Enterprise package

```text
On-prem deployment
SSO
RBAC
Audit exports
Custom domain packs
Private model gateway
Compliance reports
Dedicated support
```

---

## 23. Key Design Decisions

### Decision 1 — Framework over chatbot

Build infrastructure that runs many agents, not a single chat assistant.

### Decision 2 — Domain stack as product differentiator

Core frameworks are crowded. The differentiator is domain expertise:

```text
Cybersecurity
Research automation
Productivity behavior intelligence
Investor/GTM workflows
```

### Decision 3 — Obsidian as memory workspace

Obsidian gives a local-first, human-readable, graph-based workspace for research, decisions, and artifacts.

### Decision 4 — Evidence-first research

Research agents must produce evidence-backed claims, not generic summaries.

### Decision 5 — Guarded autonomy

Agents can reason freely, but tool execution must be governed.

### Decision 6 — Codex-friendly development

Everything must be explicit: file structure, contracts, tests, acceptance criteria, prompts.

---

## 24. Non-Negotiable Quality Rules

Codex must enforce:

```text
No untyped core modules.
No hardcoded secrets.
No direct tool execution without policy check.
No domain-specific code inside generic runtime.
No RAG answer without source metadata.
No agent run without trace.
No high-risk action without approval.
No failing tests in main branch.
No hidden global state.
No silent exception swallowing.
```

---

## 25. References and Implementation Context

These references are useful for implementation choices and should be reviewed during development:

- OpenAI Codex documentation: https://developers.openai.com/codex
- OpenAI Code Generation / Codex guide: https://developers.openai.com/api/docs/guides/code-generation
- OpenAI Agent Skills for Codex: https://developers.openai.com/codex/skills
- OpenAI Agents SDK guide: https://developers.openai.com/api/docs/guides/agents
- OpenAI Agents observability guide: https://developers.openai.com/api/docs/guides/agents/integrations-observability
- OpenAI agentic governance cookbook: https://developers.openai.com/cookbook/examples/partners/agentic_governance_guide/agentic_governance_cookbook
- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview
- LangGraph durable execution: https://docs.langchain.com/oss/python/langgraph/durable-execution
- FastAPI documentation: https://fastapi.tiangolo.com/
- FastAPI deployment documentation: https://fastapi.tiangolo.com/deployment/
- MCP introduction: https://modelcontextprotocol.io/docs/getting-started/intro
- Obsidian Local REST API: https://github.com/coddingtonbear/obsidian-local-rest-api
- Qdrant: https://qdrant.tech/
- pgvector: https://github.com/pgvector/pgvector

---

## 26. Immediate Next Action

Codex should start with:

```text
Phase 0 → Skeleton
```

Do not start with AutoResearcher.  
Do not start with Obsidian.  
Do not start with domain agents.  
Start with the production skeleton and contracts.

Correct first milestone:

```text
A running FastAPI service with Docker Compose, health endpoint, settings, database models, and test structure.
```

Only after this, implement:

```text
Contracts → Registry → Runtime → Tools → RAG → Obsidian → AutoResearcher → Domain Stacks
```
