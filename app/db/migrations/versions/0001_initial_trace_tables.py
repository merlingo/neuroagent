"""initial persistent storage schema

Revision ID: 0001_initial_trace_tables
Revises:
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_trace_tables"
down_revision = None
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        *_timestamps(),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    op.create_table(
        "domain_stacks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("domain_id", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("contract", sa.JSON(), nullable=False),
        *_timestamps(),
    )
    op.create_table(
        "agent_definitions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("agent_id", sa.String(), nullable=False, unique=True),
        sa.Column("domain_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("risk_level", sa.String(), nullable=False),
        sa.Column("contract", sa.JSON(), nullable=False),
        *_timestamps(),
    )
    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("template_id", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        *_timestamps(),
    )
    op.create_table(
        "tool_definitions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tool_id", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("risk_level", sa.String(), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("contract", sa.JSON(), nullable=False),
        *_timestamps(),
    )
    op.create_table(
        "tool_policies",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("policy_id", sa.String(), nullable=False, unique=True),
        sa.Column("domain_id", sa.String(), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False),
        *_timestamps(),
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("domain_id", sa.String(), nullable=False),
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("resolved_plan", sa.JSON(), nullable=False),
        sa.Column("final_output", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("token_usage", sa.JSON(), nullable=False),
        sa.Column("cost_estimate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_agent_runs_tenant_id", "agent_runs", ["tenant_id"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])

    op.create_table(
        "agent_steps",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("step_type", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("output_payload", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_agent_steps_run_id", "agent_steps", ["run_id"])

    op.create_table(
        "tool_calls",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("step_id", sa.String(), nullable=True),
        sa.Column("tool_name", sa.String(), nullable=False),
        sa.Column("tool_version", sa.String(), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("output_payload", sa.JSON(), nullable=True),
        sa.Column("risk_level", sa.String(), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("approval_status", sa.String(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_tool_calls_run_id", "tool_calls", ["run_id"])

    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("artifact_type", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=True),
        sa.Column("storage_uri", sa.String(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_artifacts_tenant_id", "artifacts", ["tenant_id"])
    op.create_index("ix_artifacts_run_id", "artifacts", ["run_id"])

    op.create_table(
        "documents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("domain_id", sa.String(), nullable=True),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_uri", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("hash", sa.String(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"])
    op.create_index("ix_documents_domain_id", "documents", ["domain_id"])
    op.create_index("ix_documents_hash", "documents", ["hash"])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("document_id", sa.String(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("domain_id", sa.String(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source_metadata", sa.JSON(), nullable=False),
        sa.Column("hash", sa.String(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_document_chunks_tenant_id", "document_chunks", ["tenant_id"])
    op.create_index("ix_document_chunks_domain_id", "document_chunks", ["domain_id"])
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_hash", "document_chunks", ["hash"])

    op.create_table(
        "embedding_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("chunk_id", sa.String(), nullable=False),
        sa.Column("embedding_model", sa.String(), nullable=False),
        sa.Column("vector_backend", sa.String(), nullable=False),
        sa.Column("collection_name", sa.String(), nullable=True),
        sa.Column("vector_id", sa.String(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint(
            "chunk_id",
            "embedding_model",
            "vector_backend",
            name="uq_embedding_records_chunk_model_backend",
        ),
    )
    op.create_index("ix_embedding_records_tenant_id", "embedding_records", ["tenant_id"])
    op.create_index("ix_embedding_records_document_id", "embedding_records", ["document_id"])

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_evaluation_runs_tenant_id", "evaluation_runs", ["tenant_id"])
    op.create_index("ix_evaluation_runs_run_id", "evaluation_runs", ["run_id"])

    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("eval_name", sa.String(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="1"),
        sa.Column("rubric", sa.Text(), nullable=False),
        sa.Column("findings", sa.JSON(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_evaluation_results_tenant_id", "evaluation_results", ["tenant_id"])
    op.create_index("ix_evaluation_results_run_id", "evaluation_results", ["run_id"])

    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("tool_id", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        *_timestamps(),
    )
    op.create_index("ix_approval_requests_tenant_id", "approval_requests", ["tenant_id"])
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_audit_logs_tenant_created_at", "audit_logs", ["tenant_id", "created_at"])

    op.create_table(
        "obsidian_note_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=True),
        sa.Column("agent_id", sa.String(), nullable=True),
        sa.Column("domain_id", sa.String(), nullable=True),
        sa.Column("vault_name", sa.String(), nullable=False),
        sa.Column("note_path", sa.String(), nullable=False),
        sa.Column("frontmatter", sa.JSON(), nullable=False),
        sa.Column("write_status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("artifact_id", sa.String(), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_obsidian_note_records_tenant_id", "obsidian_note_records", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_obsidian_note_records_tenant_id", table_name="obsidian_note_records")
    op.drop_table("obsidian_note_records")
    op.drop_index("ix_audit_logs_tenant_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_approval_requests_status", table_name="approval_requests")
    op.drop_index("ix_approval_requests_tenant_id", table_name="approval_requests")
    op.drop_table("approval_requests")
    op.drop_index("ix_evaluation_results_run_id", table_name="evaluation_results")
    op.drop_index("ix_evaluation_results_tenant_id", table_name="evaluation_results")
    op.drop_table("evaluation_results")
    op.drop_index("ix_evaluation_runs_run_id", table_name="evaluation_runs")
    op.drop_index("ix_evaluation_runs_tenant_id", table_name="evaluation_runs")
    op.drop_table("evaluation_runs")
    op.drop_index("ix_embedding_records_document_id", table_name="embedding_records")
    op.drop_index("ix_embedding_records_tenant_id", table_name="embedding_records")
    op.drop_table("embedding_records")
    op.drop_index("ix_document_chunks_hash", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_domain_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_tenant_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_documents_hash", table_name="documents")
    op.drop_index("ix_documents_domain_id", table_name="documents")
    op.drop_index("ix_documents_tenant_id", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_artifacts_run_id", table_name="artifacts")
    op.drop_index("ix_artifacts_tenant_id", table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_index("ix_tool_calls_run_id", table_name="tool_calls")
    op.drop_table("tool_calls")
    op.drop_index("ix_agent_steps_run_id", table_name="agent_steps")
    op.drop_table("agent_steps")
    op.drop_index("ix_agent_runs_status", table_name="agent_runs")
    op.drop_index("ix_agent_runs_tenant_id", table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_table("tool_policies")
    op.drop_table("tool_definitions")
    op.drop_table("prompt_templates")
    op.drop_table("agent_definitions")
    op.drop_table("domain_stacks")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_table("users")
    op.drop_table("tenants")
