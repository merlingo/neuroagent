"""Host (Intravision) tools executed via HTTP callback.

Intravision dispatches a run with ``_iv_tools`` (tool schemas) and ``_iv_run_id``.
These tools are not implemented in NeuroAgent; instead a handler calls back to the
Intravision API, which runs the real implementation scoped to the run's user/project
and returns the result. New host tools require no NeuroAgent change — Intravision just
adds them to its own registry and includes them in ``_iv_tools``.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.contracts.agent_contract import JsonSchema
from app.contracts.tool_contract import ToolContract
from app.settings import Settings
from app.tools.registry import ToolHandler, ToolRegistry

logger = logging.getLogger(__name__)


def _make_handler(tool_name: str, iv_run_id: str, settings: Settings) -> ToolHandler:
    """Build a handler that POSTs the tool call back to Intravision for execution."""
    def handler(payload: dict) -> dict:
        url = f"{settings.intravision_base_url.rstrip('/')}/agent-orchestration/runs/{iv_run_id}/tool-exec"
        try:
            response = httpx.post(
                url,
                headers={
                    "X-API-Key": settings.intravision_api_key,
                    "Content-Type": "application/json",
                },
                json={"toolName": tool_name, "toolInput": payload},
                timeout=settings.model_timeout_seconds,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            # Never raise — return the error so the model can react and the run continues.
            logger.warning("Intravision tool %s callback failed: %s", tool_name, exc)
            return {"error": f"Tool '{tool_name}' callback failed: {exc}"}

    return handler


def build_run_registry(
    base_registry: ToolRegistry,
    iv_tools: list[dict[str, Any]],
    iv_run_id: str,
    settings: Settings,
) -> ToolRegistry:
    """Return a run-scoped ToolRegistry = base tools + the run's Intravision tools.

    Host tools are registered low-risk / no-approval; per-tool approval is governed by
    the agent contract's ``human_approval_required_for`` on the Intravision side.
    """
    contracts = dict(base_registry.contracts)
    handlers = dict(base_registry.handlers)
    for tool in iv_tools:
        name = tool.get("name")
        if not name:
            continue
        contracts[name] = ToolContract(
            tool_id=name,
            name=name,
            version="1.0.0",
            risk_level="low",
            requires_approval=False,
            input_schema=JsonSchema.model_validate(tool.get("input_schema") or {"type": "object"}),
            allowed_domains=[],  # empty = allowed in every domain
        )
        handlers[name] = _make_handler(name, iv_run_id, settings)
    return ToolRegistry(contracts, handlers)


def to_openai_tools(iv_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map Intravision tool definitions to OpenAI function-calling schema."""
    result: list[dict[str, Any]] = []
    for tool in iv_tools:
        name = tool.get("name")
        if not name:
            continue
        result.append({
            "type": "function",
            "function": {
                "name": name,
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema") or {"type": "object", "properties": {}},
            },
        })
    return result
