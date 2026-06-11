from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.settings import Settings
from app.storage.artifacts import ArtifactObjectStorage, S3ArtifactStorage, prepare_artifact_for_storage


def _parse_dt(value: Any):
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    return value


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=UTC).isoformat()
    return str(value)


def _json_size(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return len(value.encode("utf-8"))
    return len(json.dumps(value, default=str).encode("utf-8"))


class SQLAlchemyRepository:
    def __init__(
        self,
        session_factory: sessionmaker,
        settings: Settings,
        artifact_storage: ArtifactObjectStorage | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.artifact_storage = artifact_storage

    def _session(self):
        return self.session_factory()

    def save_run(self, run: dict) -> None:
        from app.db.models import AgentRun, Tenant

        run = {**run, "tenant_id": run.get("tenant_id") or self.settings.default_tenant_id}
        with self._session() as session:
            session.merge(Tenant(id=run["tenant_id"], name=run["tenant_id"]))
            session.merge(
                AgentRun(
                    id=run["id"],
                    tenant_id=run["tenant_id"],
                    user_id=run.get("user_id", "anonymous"),
                    domain_id=run["domain_id"],
                    agent_id=run["agent_id"],
                    status=run["status"],
                    input_payload=run.get("input_payload", {}),
                    resolved_plan=run.get("resolved_plan", {}),
                    final_output=run.get("final_output"),
                    error_message=run.get("error_message"),
                    token_usage=run.get("token_usage", {}),
                    cost_estimate=run.get("cost_estimate", 0.0),
                    model=run.get("model"),
                    started_at=_parse_dt(run.get("started_at")),
                    completed_at=_parse_dt(run.get("completed_at")),
                    created_at=_parse_dt(run.get("created_at")),
                    updated_at=_parse_dt(run.get("updated_at")),
                )
            )
            session.commit()

    def list_runs(self) -> list[dict]:
        from app.db.models import AgentRun

        with self._session() as session:
            rows = session.scalars(select(AgentRun).order_by(AgentRun.created_at.desc())).all()
            return [self._run_to_dict(row, include_children=False) for row in rows]

    def get_run(self, run_id: str) -> dict | None:
        from app.db.models import AgentRun

        with self._session() as session:
            row = session.get(AgentRun, run_id)
            if row is None:
                return None
            return self._run_to_dict(row, include_children=True)

    def update_run(self, run_id: str, updates: dict) -> dict | None:
        from app.db.models import AgentRun

        with self._session() as session:
            row = session.get(AgentRun, run_id)
            if row is None:
                return None
            column_map = {
                "input_payload": "input_payload",
                "resolved_plan": "resolved_plan",
                "final_output": "final_output",
                "error_message": "error_message",
                "token_usage": "token_usage",
                "cost_estimate": "cost_estimate",
                "model": "model",
                "status": "status",
            }
            for key, attr in column_map.items():
                if key in updates:
                    setattr(row, attr, updates[key])
            row.updated_at = _parse_dt(updates.get("updated_at")) or datetime.utcnow()
            session.commit()
        return self.get_run(run_id)

    def save_step(self, step: dict) -> None:
        from app.db.models import AgentStep

        with self._session() as session:
            session.merge(
                AgentStep(
                    id=step.get("id") or str(uuid4()),
                    run_id=step["run_id"],
                    step_index=step["step_index"],
                    step_type=step.get("step_type", step.get("type", "step")),
                    name=step.get("name", step.get("step_id", "")),
                    input_payload=step.get("input_payload", {}),
                    output_payload=step.get("output_payload"),
                    status=step.get("status", "completed"),
                    error_message=step.get("error_message"),
                    started_at=_parse_dt(step.get("started_at")),
                    completed_at=_parse_dt(step.get("completed_at")),
                    created_at=_parse_dt(step.get("created_at")),
                    updated_at=_parse_dt(step.get("updated_at")),
                )
            )
            session.commit()

    def list_run_steps(self, run_id: str) -> list[dict]:
        from app.db.models import AgentStep

        with self._session() as session:
            rows = session.scalars(
                select(AgentStep).where(AgentStep.run_id == run_id).order_by(AgentStep.step_index.asc())
            ).all()
            return [self._step_to_dict(row) for row in rows]

    def save_tool_call(self, call: dict) -> None:
        from app.db.models import ToolCall

        with self._session() as session:
            session.merge(
                ToolCall(
                    id=call.get("id") or str(uuid4()),
                    run_id=call["run_id"],
                    step_id=call.get("step_id"),
                    tool_name=call["tool_name"],
                    tool_version=call.get("tool_version", "unknown"),
                    input_payload=call.get("input_payload", {}),
                    output_payload=call.get("output_payload"),
                    risk_level=call.get("risk_level", "low"),
                    approval_required=call.get("approval_required", False),
                    approval_status=call.get("approval_status", "not_required"),
                    latency_ms=call.get("latency_ms", 0),
                    error_message=call.get("error_message"),
                    created_at=_parse_dt(call.get("created_at")),
                    updated_at=_parse_dt(call.get("updated_at")),
                )
            )
            session.commit()

    def list_run_tool_calls(self, run_id: str) -> list[dict]:
        from app.db.models import ToolCall

        with self._session() as session:
            rows = session.scalars(select(ToolCall).where(ToolCall.run_id == run_id)).all()
            return [self._tool_call_to_dict(row) for row in rows]

    def save_artifact(self, artifact: dict) -> None:
        from app.db.models import Artifact

        artifact = dict(artifact)
        artifact.setdefault("id", str(uuid4()))
        artifact_storage = self.artifact_storage
        if artifact_storage is None and artifact.get("content") is not None:
            if _json_size(artifact["content"]) > self.settings.artifact_inline_max_bytes:
                artifact_storage = S3ArtifactStorage(self.settings)
        artifact = prepare_artifact_for_storage(
            artifact,
            self.settings,
            object_storage=artifact_storage,
        )
        with self._session() as session:
            session.merge(
                Artifact(
                    id=artifact["id"],
                    run_id=artifact["run_id"],
                    tenant_id=artifact.get("tenant_id") or self.settings.default_tenant_id,
                    artifact_type=artifact.get("artifact_type", "json"),
                    name=artifact.get("name", artifact["id"]),
                    content=artifact.get("content"),
                    storage_uri=artifact.get("storage_uri"),
                    metadata_=artifact.get("metadata", {}),
                    created_at=_parse_dt(artifact.get("created_at")),
                    updated_at=_parse_dt(artifact.get("updated_at")),
                )
            )
            session.commit()

    def list_run_artifacts(self, run_id: str) -> list[dict]:
        from app.db.models import Artifact

        with self._session() as session:
            rows = session.scalars(select(Artifact).where(Artifact.run_id == run_id)).all()
            return [self._artifact_to_dict(row) for row in rows]

    def save_evaluation(self, evaluation: dict) -> None:
        from app.db.models import EvaluationResult

        with self._session() as session:
            session.merge(
                EvaluationResult(
                    id=evaluation.get("id") or str(uuid4()),
                    run_id=evaluation["run_id"],
                    tenant_id=evaluation.get("tenant_id") or self.settings.default_tenant_id,
                    eval_name=evaluation.get("eval_name", evaluation.get("name", "evaluation")),
                    passed=evaluation.get("passed", True),
                    score=evaluation.get("score", 1.0),
                    rubric=evaluation.get("rubric", ""),
                    findings=evaluation.get("findings", []),
                    created_at=_parse_dt(evaluation.get("created_at")),
                    updated_at=_parse_dt(evaluation.get("updated_at")),
                )
            )
            session.commit()

    def list_run_evaluations(self, run_id: str) -> list[dict]:
        from app.db.models import EvaluationResult

        with self._session() as session:
            rows = session.scalars(select(EvaluationResult).where(EvaluationResult.run_id == run_id)).all()
            return [self._evaluation_to_dict(row) for row in rows]

    def save_approval(self, approval: dict) -> None:
        from app.db.models import ApprovalRequest

        with self._session() as session:
            session.merge(
                ApprovalRequest(
                    id=approval["id"],
                    tenant_id=approval.get("tenant_id") or self.settings.default_tenant_id,
                    run_id=approval["run_id"],
                    tool_id=approval["tool_id"],
                    reason=approval.get("reason", ""),
                    status=approval.get("status", "pending"),
                    created_at=_parse_dt(approval.get("created_at")),
                    updated_at=_parse_dt(approval.get("updated_at")),
                )
            )
            session.commit()

    def list_pending_approvals(self) -> list[dict]:
        from app.db.models import ApprovalRequest

        with self._session() as session:
            rows = session.scalars(select(ApprovalRequest).where(ApprovalRequest.status == "pending")).all()
            return [self._approval_to_dict(row) for row in rows]

    def get_approval(self, approval_id: str) -> dict | None:
        from app.db.models import ApprovalRequest

        with self._session() as session:
            row = session.get(ApprovalRequest, approval_id)
            return None if row is None else self._approval_to_dict(row)

    def update_approval(self, approval_id: str, status: str) -> dict | None:
        from app.db.models import ApprovalRequest

        with self._session() as session:
            row = session.get(ApprovalRequest, approval_id)
            if row is None:
                return None
            row.status = status
            row.updated_at = datetime.utcnow()
            session.commit()
        return self.get_approval(approval_id)

    def save_document(self, document: dict) -> None:
        from app.db.models import Document

        document = {**document, "tenant_id": document.get("tenant_id") or self.settings.default_tenant_id}
        document_id = document.get("id") or document.get("document_id") or str(uuid4())
        with self._session() as session:
            session.merge(
                Document(
                    id=document_id,
                    tenant_id=document["tenant_id"],
                    domain_id=document.get("domain_id"),
                    source_type=document.get("source_type", "text"),
                    source_uri=document.get("source_uri"),
                    title=document.get("title", document_id),
                    hash=document.get("hash")
                    or hashlib.sha256(document.get("content", "").encode("utf-8")).hexdigest(),
                    metadata_=document.get("metadata", {}),
                    created_at=_parse_dt(document.get("created_at")),
                    updated_at=_parse_dt(document.get("updated_at")),
                )
            )
            session.commit()

    def list_documents(self, tenant_id: str | None = None, domain_id: str | None = None) -> list[dict]:
        from app.db.models import Document

        with self._session() as session:
            stmt = select(Document)
            if tenant_id:
                stmt = stmt.where(Document.tenant_id == tenant_id)
            if domain_id:
                stmt = stmt.where(Document.domain_id == domain_id)
            return [self._document_to_dict(row) for row in session.scalars(stmt).all()]

    def get_document(self, document_id: str) -> dict | None:
        from app.db.models import Document

        with self._session() as session:
            row = session.get(Document, document_id)
            return None if row is None else self._document_to_dict(row)

    def save_document_chunk(self, chunk: dict) -> None:
        from app.db.models import DocumentChunk

        with self._session() as session:
            session.merge(
                DocumentChunk(
                    id=chunk.get("id") or chunk.get("chunk_id"),
                    document_id=chunk["document_id"],
                    tenant_id=chunk.get("tenant_id") or self.settings.default_tenant_id,
                    domain_id=chunk.get("domain_id"),
                    chunk_index=chunk.get("chunk_index", 0),
                    text=chunk["text"],
                    source_metadata=chunk.get("metadata", chunk.get("source_metadata", {})),
                    hash=chunk.get("hash") or hashlib.sha256(chunk["text"].encode("utf-8")).hexdigest(),
                    created_at=_parse_dt(chunk.get("created_at")),
                    updated_at=_parse_dt(chunk.get("updated_at")),
                )
            )
            session.commit()

    def list_document_chunks(self, document_id: str) -> list[dict]:
        from app.db.models import DocumentChunk

        with self._session() as session:
            rows = session.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.chunk_index.asc())
            ).all()
            return [self._chunk_to_dict(row) for row in rows]

    def save_embedding_record(self, record: dict) -> None:
        from app.db.models import EmbeddingRecord

        with self._session() as session:
            session.merge(
                EmbeddingRecord(
                    id=record.get("id") or str(uuid4()),
                    tenant_id=record.get("tenant_id") or self.settings.default_tenant_id,
                    document_id=record["document_id"],
                    chunk_id=record["chunk_id"],
                    embedding_model=record["embedding_model"],
                    vector_backend=record["vector_backend"],
                    collection_name=record.get("collection_name"),
                    vector_id=record["vector_id"],
                    created_at=_parse_dt(record.get("created_at")),
                    updated_at=_parse_dt(record.get("updated_at")),
                )
            )
            session.commit()

    def list_embedding_records(self, document_id: str | None = None) -> list[dict]:
        from app.db.models import EmbeddingRecord

        with self._session() as session:
            stmt = select(EmbeddingRecord)
            if document_id:
                stmt = stmt.where(EmbeddingRecord.document_id == document_id)
            return [self._embedding_to_dict(row) for row in session.scalars(stmt).all()]

    def append_audit_log(self, event: dict) -> None:
        from app.db.models import AuditLog

        with self._session() as session:
            session.merge(
                AuditLog(
                    id=event.get("id") or str(uuid4()),
                    tenant_id=event.get("tenant_id") or self.settings.default_tenant_id,
                    actor_id=event.get("actor_id"),
                    action=event["action"],
                    resource_type=event["resource_type"],
                    resource_id=event.get("resource_id"),
                    payload=event.get("payload", {}),
                    created_at=_parse_dt(event.get("created_at")),
                    updated_at=_parse_dt(event.get("updated_at")),
                )
            )
            session.commit()

    def list_audit_logs(self, tenant_id: str | None = None) -> list[dict]:
        from app.db.models import AuditLog

        with self._session() as session:
            stmt = select(AuditLog)
            if tenant_id:
                stmt = stmt.where(AuditLog.tenant_id == tenant_id)
            rows = session.scalars(stmt.order_by(AuditLog.created_at.desc())).all()
            return [self._audit_to_dict(row) for row in rows]

    def _run_to_dict(self, row, include_children: bool) -> dict:
        data = {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "user_id": row.user_id,
            "domain_id": row.domain_id,
            "agent_id": row.agent_id,
            "status": row.status,
            "input_payload": row.input_payload,
            "resolved_plan": row.resolved_plan,
            "final_output": row.final_output,
            "error_message": row.error_message,
            "token_usage": row.token_usage,
            "cost_estimate": row.cost_estimate,
            "model": row.model,
            "started_at": _iso(row.started_at),
            "completed_at": _iso(row.completed_at),
            "created_at": _iso(row.created_at),
            "updated_at": _iso(row.updated_at),
        }
        if include_children:
            data.update(
                steps=self.list_run_steps(row.id),
                tool_calls=self.list_run_tool_calls(row.id),
                artifacts=self.list_run_artifacts(row.id),
                evaluations=self.list_run_evaluations(row.id),
            )
        return data

    def _step_to_dict(self, row) -> dict:
        return {
            "id": row.id,
            "run_id": row.run_id,
            "step_index": row.step_index,
            "step_type": row.step_type,
            "name": row.name,
            "input_payload": row.input_payload,
            "output_payload": row.output_payload,
            "status": row.status,
            "error_message": row.error_message,
            "created_at": _iso(row.created_at),
        }

    def _tool_call_to_dict(self, row) -> dict:
        return {
            "id": row.id,
            "run_id": row.run_id,
            "step_id": row.step_id,
            "tool_name": row.tool_name,
            "tool_version": row.tool_version,
            "input_payload": row.input_payload,
            "output_payload": row.output_payload,
            "risk_level": row.risk_level,
            "approval_required": row.approval_required,
            "approval_status": row.approval_status,
            "latency_ms": row.latency_ms,
            "error_message": row.error_message,
            "created_at": _iso(row.created_at),
        }

    def _artifact_to_dict(self, row) -> dict:
        return {
            "id": row.id,
            "run_id": row.run_id,
            "tenant_id": row.tenant_id,
            "artifact_type": row.artifact_type,
            "name": row.name,
            "content": row.content,
            "storage_uri": row.storage_uri,
            "metadata": row.metadata_,
            "created_at": _iso(row.created_at),
        }

    def _evaluation_to_dict(self, row) -> dict:
        return {
            "id": row.id,
            "run_id": row.run_id,
            "tenant_id": row.tenant_id,
            "eval_name": row.eval_name,
            "passed": row.passed,
            "score": row.score,
            "rubric": row.rubric,
            "findings": row.findings,
        }

    def _approval_to_dict(self, row) -> dict:
        return {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "run_id": row.run_id,
            "tool_id": row.tool_id,
            "reason": row.reason,
            "status": row.status,
            "created_at": _iso(row.created_at),
        }

    def _document_to_dict(self, row) -> dict:
        return {
            "id": row.id,
            "document_id": row.id,
            "tenant_id": row.tenant_id,
            "domain_id": row.domain_id,
            "source_type": row.source_type,
            "source_uri": row.source_uri,
            "title": row.title,
            "hash": row.hash,
            "metadata": row.metadata_,
        }

    def _chunk_to_dict(self, row) -> dict:
        return {
            "id": row.id,
            "chunk_id": row.id,
            "document_id": row.document_id,
            "tenant_id": row.tenant_id,
            "domain_id": row.domain_id,
            "chunk_index": row.chunk_index,
            "text": row.text,
            "metadata": row.source_metadata,
            "hash": row.hash,
        }

    def _embedding_to_dict(self, row) -> dict:
        return {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "document_id": row.document_id,
            "chunk_id": row.chunk_id,
            "embedding_model": row.embedding_model,
            "vector_backend": row.vector_backend,
            "collection_name": row.collection_name,
            "vector_id": row.vector_id,
        }

    def _audit_to_dict(self, row) -> dict:
        return {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "actor_id": row.actor_id,
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "payload": row.payload,
            "created_at": _iso(row.created_at),
        }
