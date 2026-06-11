from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from app.settings import Settings, get_settings
from app.storage.artifacts import prepare_artifact_for_storage


class Repository(Protocol):
    def save_run(self, run: dict) -> None: ...
    def list_runs(self) -> list[dict]: ...
    def get_run(self, run_id: str) -> dict | None: ...
    def update_run(self, run_id: str, updates: dict) -> dict | None: ...
    def save_step(self, step: dict) -> None: ...
    def list_run_steps(self, run_id: str) -> list[dict]: ...
    def save_tool_call(self, call: dict) -> None: ...
    def list_run_tool_calls(self, run_id: str) -> list[dict]: ...
    def save_artifact(self, artifact: dict) -> None: ...
    def list_run_artifacts(self, run_id: str) -> list[dict]: ...
    def save_evaluation(self, evaluation: dict) -> None: ...
    def list_run_evaluations(self, run_id: str) -> list[dict]: ...
    def save_approval(self, approval: dict) -> None: ...
    def list_pending_approvals(self) -> list[dict]: ...
    def get_approval(self, approval_id: str) -> dict | None: ...
    def update_approval(self, approval_id: str, status: str) -> dict | None: ...
    def save_document(self, document: dict) -> None: ...
    def list_documents(self, tenant_id: str | None = None, domain_id: str | None = None) -> list[dict]: ...
    def get_document(self, document_id: str) -> dict | None: ...
    def save_document_chunk(self, chunk: dict) -> None: ...
    def list_document_chunks(self, document_id: str) -> list[dict]: ...
    def save_embedding_record(self, record: dict) -> None: ...
    def list_embedding_records(self, document_id: str | None = None) -> list[dict]: ...
    def append_audit_log(self, event: dict) -> None: ...
    def list_audit_logs(self, tenant_id: str | None = None) -> list[dict]: ...


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json_size(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bytes):
        return len(value)
    if isinstance(value, str):
        return len(value.encode("utf-8"))
    return len(json.dumps(value, default=str).encode("utf-8"))


def _ensure_tenant(payload: dict, settings: Settings) -> dict:
    if not payload.get("tenant_id"):
        payload = {**payload, "tenant_id": settings.default_tenant_id}
    return payload


class InMemoryRepository:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.runs: dict[str, dict] = {}
        self.steps: list[dict] = []
        self.tool_calls: list[dict] = []
        self.artifacts: list[dict] = []
        self.evaluations: list[dict] = []
        self.evaluation_runs: list[dict] = []
        self.approvals: list[dict] = []
        self.documents: dict[str, dict] = {}
        self.document_chunks: list[dict] = []
        self.embedding_records: list[dict] = []
        self.audit_logs: list[dict] = []

    def save_run(self, run: dict) -> None:
        self.runs[run["id"]] = _ensure_tenant(run, self.settings)

    def list_runs(self) -> list[dict]:
        return sorted(self.runs.values(), key=lambda run: run.get("created_at", ""), reverse=True)

    def get_run(self, run_id: str) -> dict | None:
        run = self.runs.get(run_id)
        if run is None:
            return None
        return {
            **run,
            "steps": self.list_run_steps(run_id),
            "tool_calls": self.list_run_tool_calls(run_id),
            "artifacts": self.list_run_artifacts(run_id),
            "evaluations": self.list_run_evaluations(run_id),
        }

    def update_run(self, run_id: str, updates: dict) -> dict | None:
        run = self.runs.get(run_id)
        if run is None:
            return None
        run.update({**updates, "updated_at": updates.get("updated_at", _now())})
        return self.get_run(run_id)

    def save_step(self, step: dict) -> None:
        self.steps.append(step)

    def list_run_steps(self, run_id: str) -> list[dict]:
        return sorted(
            [step for step in self.steps if step["run_id"] == run_id],
            key=lambda step: step["step_index"],
        )

    def save_tool_call(self, call: dict) -> None:
        self.tool_calls.append(call)

    def list_run_tool_calls(self, run_id: str) -> list[dict]:
        return [call for call in self.tool_calls if call["run_id"] == run_id]

    def save_artifact(self, artifact: dict) -> None:
        artifact = dict(artifact)
        artifact.setdefault("id", str(uuid4()))
        artifact.setdefault("created_at", _now())
        artifact.setdefault("updated_at", artifact["created_at"])
        artifact = prepare_artifact_for_storage(
            artifact,
            self.settings,
            object_storage=None,
            memory_fallback=True,
        )
        self.artifacts.append(artifact)

    def list_run_artifacts(self, run_id: str) -> list[dict]:
        return [artifact for artifact in self.artifacts if artifact["run_id"] == run_id]

    def save_evaluation(self, evaluation: dict) -> None:
        evaluation = dict(evaluation)
        evaluation.setdefault("id", str(uuid4()))
        evaluation.setdefault("created_at", _now())
        self.evaluations.append(evaluation)

    def list_run_evaluations(self, run_id: str) -> list[dict]:
        return [evaluation for evaluation in self.evaluations if evaluation["run_id"] == run_id]

    def save_approval(self, approval: dict) -> None:
        self.approvals.append(dict(approval))

    def list_pending_approvals(self) -> list[dict]:
        return [approval for approval in self.approvals if approval["status"] == "pending"]

    def get_approval(self, approval_id: str) -> dict | None:
        for approval in self.approvals:
            if approval["id"] == approval_id:
                return approval
        return None

    def update_approval(self, approval_id: str, status: str) -> dict | None:
        approval = self.get_approval(approval_id)
        if approval is None:
            return None
        approval["status"] = status
        return approval

    def save_document(self, document: dict) -> None:
        document = _ensure_tenant(dict(document), self.settings)
        document.setdefault("id", document.get("document_id", str(uuid4())))
        document.setdefault("document_id", document["id"])
        document.setdefault("hash", hashlib.sha256(document.get("content", "").encode()).hexdigest())
        document.setdefault("created_at", _now())
        self.documents[document["id"]] = document

    def list_documents(self, tenant_id: str | None = None, domain_id: str | None = None) -> list[dict]:
        docs = list(self.documents.values())
        if tenant_id:
            docs = [doc for doc in docs if doc.get("tenant_id") == tenant_id]
        if domain_id:
            docs = [doc for doc in docs if doc.get("domain_id") == domain_id]
        return docs

    def get_document(self, document_id: str) -> dict | None:
        return self.documents.get(document_id)

    def save_document_chunk(self, chunk: dict) -> None:
        self.document_chunks.append(_ensure_tenant(dict(chunk), self.settings))

    def list_document_chunks(self, document_id: str) -> list[dict]:
        return [chunk for chunk in self.document_chunks if chunk["document_id"] == document_id]

    def save_embedding_record(self, record: dict) -> None:
        existing = [
            item
            for item in self.embedding_records
            if item["chunk_id"] == record["chunk_id"]
            and item["embedding_model"] == record["embedding_model"]
            and item["vector_backend"] == record["vector_backend"]
        ]
        for item in existing:
            self.embedding_records.remove(item)
        self.embedding_records.append(dict(record))

    def list_embedding_records(self, document_id: str | None = None) -> list[dict]:
        if document_id is None:
            return list(self.embedding_records)
        return [record for record in self.embedding_records if record["document_id"] == document_id]

    def append_audit_log(self, event: dict) -> None:
        event = _ensure_tenant(dict(event), self.settings)
        event.setdefault("id", str(uuid4()))
        event.setdefault("created_at", _now())
        self.audit_logs.append(event)

    def list_audit_logs(self, tenant_id: str | None = None) -> list[dict]:
        if tenant_id is None:
            return list(self.audit_logs)
        return [event for event in self.audit_logs if event["tenant_id"] == tenant_id]


repository = InMemoryRepository()
_sql_repository: Repository | None = None


def get_repository(settings: Settings | None = None) -> Repository:
    settings = settings or get_settings()
    if settings.repository_backend == "memory":
        return repository
    if settings.repository_backend == "postgres":
        if settings.app_env == "production" and not settings.database_url:
            raise RuntimeError("DATABASE_URL is required when APP_ENV=production")
        if not settings.database_url:
            if settings.app_env == "development":
                return repository
            raise RuntimeError("DATABASE_URL is required for postgres repository backend")
        global _sql_repository
        if _sql_repository is None:
            from app.db.session import get_session_local
            from app.db.sqlalchemy_repository import SQLAlchemyRepository

            _sql_repository = SQLAlchemyRepository(get_session_local(), settings)
        return _sql_repository
    raise RuntimeError(f"Unsupported REPOSITORY_BACKEND={settings.repository_backend}")
