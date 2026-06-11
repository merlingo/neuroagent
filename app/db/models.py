from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"))
    email: Mapped[str] = mapped_column(String)
    __table_args__ = (Index("ix_users_tenant_id", "tenant_id"),)


class DomainStack(Base, TimestampMixin):
    __tablename__ = "domain_stacks"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    domain_id: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    version: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    contract: Mapped[dict[str, Any]] = mapped_column(JSON)


class AgentDefinition(Base, TimestampMixin):
    __tablename__ = "agent_definitions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_id: Mapped[str] = mapped_column(String, unique=True)
    domain_id: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    version: Mapped[str] = mapped_column(String)
    risk_level: Mapped[str] = mapped_column(String)
    contract: Mapped[dict[str, Any]] = mapped_column(JSON)


class PromptTemplate(Base, TimestampMixin):
    __tablename__ = "prompt_templates"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    template_id: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    version: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class ToolDefinition(Base, TimestampMixin):
    __tablename__ = "tool_definitions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tool_id: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    version: Mapped[str] = mapped_column(String)
    risk_level: Mapped[str] = mapped_column(String)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    contract: Mapped[dict[str, Any]] = mapped_column(JSON)


class ToolPolicy(Base, TimestampMixin):
    __tablename__ = "tool_policies"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    policy_id: Mapped[str] = mapped_column(String, unique=True)
    domain_id: Mapped[str] = mapped_column(String)
    rules: Mapped[dict[str, Any]] = mapped_column(JSON)


class AgentRun(Base, TimestampMixin):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String)
    user_id: Mapped[str] = mapped_column(String)
    domain_id: Mapped[str] = mapped_column(String)
    agent_id: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    resolved_plan: Mapped[dict[str, Any]] = mapped_column(JSON)
    final_output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_usage: Mapped[dict[str, Any]] = mapped_column(JSON)
    cost_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    __table_args__ = (
        Index("ix_agent_runs_tenant_id", "tenant_id"),
        Index("ix_agent_runs_status", "status"),
    )


class AgentStep(Base, TimestampMixin):
    __tablename__ = "agent_steps"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"))
    step_index: Mapped[int] = mapped_column(Integer)
    step_type: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    output_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    __table_args__ = (Index("ix_agent_steps_run_id", "run_id"),)


class ToolCall(Base, TimestampMixin):
    __tablename__ = "tool_calls"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"))
    step_id: Mapped[str | None] = mapped_column(String, nullable=True)
    tool_name: Mapped[str] = mapped_column(String)
    tool_version: Mapped[str] = mapped_column(String)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    output_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    risk_level: Mapped[str] = mapped_column(String)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_status: Mapped[str] = mapped_column(String)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (Index("ix_tool_calls_run_id", "run_id"),)


class Artifact(Base, TimestampMixin):
    __tablename__ = "artifacts"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"))
    tenant_id: Mapped[str] = mapped_column(String)
    artifact_type: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    content: Mapped[dict[str, Any] | list[Any] | str | None] = mapped_column(JSON, nullable=True)
    storage_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    __table_args__ = (
        Index("ix_artifacts_tenant_id", "tenant_id"),
        Index("ix_artifacts_run_id", "run_id"),
    )


class Document(Base, TimestampMixin):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String)
    domain_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_type: Mapped[str] = mapped_column(String)
    source_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String)
    hash: Mapped[str] = mapped_column(String)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    __table_args__ = (
        Index("ix_documents_tenant_id", "tenant_id"),
        Index("ix_documents_domain_id", "domain_id"),
        Index("ix_documents_hash", "hash"),
    )


class DocumentChunk(Base, TimestampMixin):
    __tablename__ = "document_chunks"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    tenant_id: Mapped[str] = mapped_column(String)
    domain_id: Mapped[str | None] = mapped_column(String, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(JSON)
    hash: Mapped[str] = mapped_column(String)
    __table_args__ = (
        Index("ix_document_chunks_tenant_id", "tenant_id"),
        Index("ix_document_chunks_domain_id", "domain_id"),
        Index("ix_document_chunks_document_id", "document_id"),
        Index("ix_document_chunks_hash", "hash"),
    )


class EmbeddingRecord(Base, TimestampMixin):
    __tablename__ = "embedding_records"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(String)
    chunk_id: Mapped[str] = mapped_column(String)
    tenant_id: Mapped[str] = mapped_column(String)
    embedding_model: Mapped[str] = mapped_column(String)
    vector_backend: Mapped[str] = mapped_column(String)
    collection_name: Mapped[str | None] = mapped_column(String, nullable=True)
    vector_id: Mapped[str] = mapped_column(String)
    __table_args__ = (
        UniqueConstraint(
            "chunk_id",
            "embedding_model",
            "vector_backend",
            name="uq_embedding_records_chunk_model_backend",
        ),
        Index("ix_embedding_records_tenant_id", "tenant_id"),
        Index("ix_embedding_records_document_id", "document_id"),
    )


class EvaluationRun(Base, TimestampMixin):
    __tablename__ = "evaluation_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"))
    status: Mapped[str] = mapped_column(String)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    __table_args__ = (
        Index("ix_evaluation_runs_tenant_id", "tenant_id"),
        Index("ix_evaluation_runs_run_id", "run_id"),
    )


class EvaluationResult(Base, TimestampMixin):
    __tablename__ = "evaluation_results"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"))
    eval_name: Mapped[str] = mapped_column(String)
    passed: Mapped[bool] = mapped_column(Boolean)
    score: Mapped[float] = mapped_column(Float, default=1.0)
    rubric: Mapped[str] = mapped_column(Text, default="")
    findings: Mapped[list[Any]] = mapped_column(JSON, default=list)
    __table_args__ = (
        Index("ix_evaluation_results_tenant_id", "tenant_id"),
        Index("ix_evaluation_results_run_id", "run_id"),
    )


class ApprovalRequest(Base, TimestampMixin):
    __tablename__ = "approval_requests"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String)
    run_id: Mapped[str] = mapped_column(String)
    tool_id: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="pending")
    __table_args__ = (
        Index("ix_approval_requests_tenant_id", "tenant_id"),
        Index("ix_approval_requests_status", "status"),
    )


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String)
    actor_id: Mapped[str | None] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(String)
    resource_type: Mapped[str] = mapped_column(String)
    resource_id: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    __table_args__ = (Index("ix_audit_logs_tenant_created_at", "tenant_id", "created_at"),)


class ObsidianNoteRecord(Base, TimestampMixin):
    __tablename__ = "obsidian_note_records"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String)
    run_id: Mapped[str | None] = mapped_column(String, nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String, nullable=True)
    domain_id: Mapped[str | None] = mapped_column(String, nullable=True)
    vault_name: Mapped[str] = mapped_column(String)
    note_path: Mapped[str] = mapped_column(String)
    frontmatter: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    write_status: Mapped[str] = mapped_column(String, default="pending")
    artifact_id: Mapped[str | None] = mapped_column(String, nullable=True)
    __table_args__ = (Index("ix_obsidian_note_records_tenant_id", "tenant_id"),)
