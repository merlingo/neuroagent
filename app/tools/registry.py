from __future__ import annotations

from pathlib import Path
from typing import Callable

import yaml

from app.contracts.tool_contract import ToolContract
from app.core.errors import ContractNotFoundError
from app.obsidian.note_writer import ObsidianNoteWriter
from app.tools import citation_tools, file_tools, github_tools, rag_tools, shell_tools, web_search
from app.tools.domain_tools import mitre, sigma, yara


ToolHandler = Callable[[dict], dict]


def echo_tool(payload: dict) -> dict:
    return {"echo": payload}


def obsidian_write_note(payload: dict) -> dict:
    return ObsidianNoteWriter().write_note(
        title=payload.get("title", "Untitled"),
        body=payload.get("body", payload.get("content", "")),
        folder=payload.get("folder", "03_Agent_Runs"),
    )


DEFAULT_HANDLERS: dict[str, ToolHandler] = {
    "local.echo": echo_tool,
    "file.write_artifact": file_tools.write_artifact,
    "file.read_file": file_tools.read_file,
    "file.write_file": file_tools.write_file,
    "file.update_file": file_tools.update_file,
    "file.delete_file": file_tools.delete_file,
    "obsidian.write_note": obsidian_write_note,
    "rag.search": rag_tools.search,
    "rag.ingest_document": rag_tools.ingest_document,
    "rag.index_document": rag_tools.index_document,
    "rag.delete_document_vectors": rag_tools.delete_document_vectors,
    "web.search": web_search.search,
    "citation.verify": citation_tools.verify,
    "sigma.validate_yaml": sigma.validate_yaml,
    "yara.validate_rule": yara.validate_rule,
    "mitre.lookup": mitre.lookup,
    "github.get_repo": github_tools.get_repo,
    "github.get_issue": github_tools.get_issue,
    "github.list_issues": github_tools.list_issues,
    "github.create_issue": github_tools.create_issue,
    "github.create_issue_comment": github_tools.create_issue_comment,
    "github.get_file": github_tools.get_file,
    "github.update_file": github_tools.update_file,
    "shell.execute": shell_tools.request_shell_approval,
}


class ToolRegistry:
    def __init__(
        self,
        contracts: dict[str, ToolContract],
        handlers: dict[str, ToolHandler] | None = None,
    ) -> None:
        self.contracts = contracts
        self.handlers = dict(DEFAULT_HANDLERS)
        if handlers:
            self.handlers.update(handlers)

    @classmethod
    def from_default_path(cls) -> "ToolRegistry":
        return cls.from_yaml_file(Path("app/tools/tools.yaml"))

    @classmethod
    def from_yaml_file(cls, path: Path) -> "ToolRegistry":
        raw = yaml.safe_load(path.read_text()) or {}
        contracts = {
            item["tool_id"]: ToolContract.model_validate(item) for item in raw.get("tools", [])
        }
        return cls(contracts)

    def list(self) -> list[ToolContract]:
        return sorted(self.contracts.values(), key=lambda item: item.tool_id)

    def get(self, tool_id: str) -> ToolContract:
        try:
            return self.contracts[tool_id]
        except KeyError as exc:
            raise ContractNotFoundError(f"Tool {tool_id} not found") from exc

    def missing_handlers(self) -> list[str]:
        return sorted(tool_id for tool_id in self.contracts if tool_id not in self.handlers)

    def run(self, tool_id: str, payload: dict) -> dict:
        self.get(tool_id)
        try:
            handler = self.handlers[tool_id]
        except KeyError as exc:
            raise ContractNotFoundError(f"Tool handler for {tool_id} not found") from exc
        return handler(payload)
