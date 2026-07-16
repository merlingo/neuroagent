"""Dynamic (LLM-driven) tool-calling loop.

Used when an agent has Intravision host tools (passed via ``input_payload._iv_tools``).
Unlike the static SimplePlanner path, the LLM decides which tools to call; each call is
executed via ToolExecutor (policy + persistence), and the result is fed back until the
model produces a final answer. Uses OpenAI-style function-calling over the
``/chat/completions`` endpoint (LiteLLM), which is reliable with Claude.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx

from app.contracts.agent_contract import AgentContract
from app.settings import Settings
from app.tools.executor import ToolExecutor
from app.tools.intravision_tools import to_openai_tools

logger = logging.getLogger(__name__)


def _estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return round((prompt_tokens + completion_tokens) * 0.000001, 6)


def _user_prompt(input_payload: dict[str, Any]) -> str:
    messages = input_payload.get("messages")
    if isinstance(messages, list) and messages:
        return "\n\n".join(
            str(m.get("content", "")) for m in messages if isinstance(m, dict)
        )
    clean = {
        k: v for k, v in input_payload.items()
        if not k.startswith("_iv") and k not in ("tenant_id", "user_id")
    }
    return json.dumps(clean, ensure_ascii=False)


def _system_prompt(agent: AgentContract) -> str:
    schema = json.dumps(agent.output_schema.model_dump(), ensure_ascii=False)
    return (
        f"You are {agent.name}. {agent.role}\n"
        f"Goal: {agent.goal}\n\n"
        "Use the available tools to ACTUALLY perform the requested work — do not merely "
        "describe what you would do. Call a tool whenever an action is needed (for example, "
        "creating a workspace page or a task). You may call tools multiple times. When the "
        "work is fully done, reply with a final message (no tool call) summarizing what you "
        "accomplished. If possible, format that final message as a JSON object matching this "
        f"output schema:\n{schema}"
    )


def _chat_completion(
    settings: Settings, model: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
) -> dict[str, Any]:
    url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": settings.model_temperature,
        "max_tokens": settings.model_max_tokens,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    response = httpx.post(
        url,
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        json=payload,
        timeout=settings.model_timeout_seconds,
    )
    response.raise_for_status()
    return response.json()


def _coerce_final_output(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    fenced = text
    if fenced.startswith("```"):
        fenced = fenced.strip("`")
        fenced = fenced.split("\n", 1)[1] if "\n" in fenced else fenced
    try:
        value = json.loads(fenced)
        if isinstance(value, dict):
            return value
    except (json.JSONDecodeError, ValueError):
        pass
    # Plain text final answer — wrap to satisfy the common {result, artifacts} schema.
    return {"result": content, "artifacts": []}


def run_tool_loop(
    agent: AgentContract,
    input_payload: dict[str, Any],
    tool_executor: ToolExecutor,
    run_id: str,
    iv_tools: list[dict[str, Any]],
    *,
    model_override: str | None,
    max_steps: int,
    max_tokens: int | None,
    settings: Settings,
) -> dict[str, Any]:
    model = model_override or settings.default_model
    openai_tools = to_openai_tools(iv_tools)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _system_prompt(agent)},
        {"role": "user", "content": _user_prompt(input_payload)},
    ]

    steps: list[dict[str, Any]] = []
    tool_calls: list[dict[str, Any]] = []
    prompt_tokens = 0
    completion_tokens = 0
    used_model = model
    final_output: dict[str, Any] | None = None
    status = "completed"

    for index in range(max_steps):
        if max_tokens is not None and (prompt_tokens + completion_tokens) >= max_tokens:
            status = "max_tokens"
            break

        started_at = datetime.now(UTC).isoformat()
        data = _chat_completion(settings, model, messages, openai_tools)
        used_model = data.get("model", model)
        usage = data.get("usage") or {}
        prompt_tokens += usage.get("prompt_tokens", 0)
        completion_tokens += usage.get("completion_tokens", 0)

        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        requested = message.get("tool_calls") or []

        if not requested:
            # No tool call → this is the final answer.
            final_output = _coerce_final_output(message.get("content") or "")
            steps.append(_step_record(run_id, index, "agent_reasoning", {"messages": "final"}, final_output, started_at))
            break

        # Record the assistant turn that requested tools, then execute each.
        messages.append({"role": "assistant", "content": message.get("content"), "tool_calls": requested})
        step_id = str(uuid4())
        step_outputs: list[dict[str, Any]] = []
        for tc in requested:
            fn = tc.get("function") or {}
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except (json.JSONDecodeError, ValueError):
                args = {}
            call = tool_executor.execute(run_id, agent, name, args, step_id=step_id)
            output = call.get("output_payload")
            tool_calls.append(call)
            step_outputs.append({"tool": name, "output": output})
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id"),
                "content": json.dumps(output, ensure_ascii=False),
            })
        steps.append(
            {**_step_record(run_id, index, "tool_call", {"tool_calls": requested}, {"results": step_outputs}, started_at), "step_id": step_id}
        )
    else:
        status = "max_steps"

    if final_output is None and status == "completed":
        status = "max_steps"

    return {
        "steps": steps,
        "tool_calls": tool_calls,
        "final_output": final_output,
        "token_usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
        "cost_estimate": _estimate_cost(prompt_tokens, completion_tokens),
        "model": used_model,
        "status": status,
    }


def _step_record(
    run_id: str, index: int, step_type: str, input_payload: dict[str, Any],
    output: dict[str, Any] | None, started_at: str,
) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "run_id": run_id,
        "step_index": index,
        "step_id": f"step_{index}",
        "name": step_type,
        "step_type": step_type,
        "input_payload": input_payload,
        "status": "completed",
        "output_payload": output,
        "error_message": None,
        "started_at": started_at,
        "completed_at": datetime.now(UTC).isoformat(),
    }
