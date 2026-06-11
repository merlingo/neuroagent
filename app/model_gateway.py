from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.contracts.agent_contract import AgentContract
from app.contracts.workflow_contract import ExecutionPlan
from app.settings import Settings, get_settings


@dataclass(frozen=True)
class ModelResponse:
    content: dict[str, Any]
    token_usage: dict[str, int]
    cost_estimate: float
    model: str


class ModelGateway(Protocol):
    def complete(
        self,
        agent: AgentContract,
        plan: ExecutionPlan,
        input_payload: dict[str, Any],
        findings: list[str],
    ) -> ModelResponse:
        ...


class ModelGatewayError(RuntimeError):
    pass


class MissingModelProviderConfig(ModelGatewayError):
    pass


def _estimate_cost(token_usage: dict[str, int]) -> float:
    return round((token_usage.get("prompt_tokens", 0) + token_usage.get("completion_tokens", 0)) * 0.000001, 6)


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ModelGatewayError("Model response was not valid JSON") from exc
    if not isinstance(value, dict):
        raise ModelGatewayError("Model response JSON must be an object")
    return value


def _build_prompt(
    agent: AgentContract,
    plan: ExecutionPlan,
    input_payload: dict[str, Any],
    findings: list[str],
) -> list[dict[str, str]]:
    system = (
        "You are executing a governed NeuroAgent run. "
        "Return only one JSON object that satisfies the provided output schema. "
        "Do not wrap the JSON in markdown and do not include commentary outside JSON."
    )
    user = {
        "agent": {
            "id": agent.agent_id,
            "name": agent.name,
            "role": agent.role,
            "goal": agent.goal,
            "domain": agent.domain,
        },
        "input_payload": input_payload,
        "execution_plan": plan.model_dump(),
        "findings": findings,
        "output_schema": agent.output_schema.model_dump(),
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]


def _messages_text(messages: list[dict[str, str]]) -> str:
    return "\n\n".join(f"{message['role'].upper()}:\n{message['content']}" for message in messages)


def _http_error(exc: httpx.HTTPError, provider: str) -> ModelGatewayError:
    return ModelGatewayError(f"{provider} model request failed: {exc}")


class StubModelGateway:
    def __init__(self, model: str = "stub-model") -> None:
        self.model = model

    def complete(
        self,
        agent: AgentContract,
        plan: ExecutionPlan,
        input_payload: dict[str, Any],
        findings: list[str],
    ) -> ModelResponse:
        output: dict[str, Any] = {
            "summary": f"{agent.name} completed a governed stub run.",
            "evidence": [],
            "confidence_score": 0.55,
        }
        if "sigma_rule" in agent.output_schema.properties:
            output["sigma_rule"] = {
                "title": "Stub Sigma Detection",
                "status": "test",
                "logsource": {"product": input_payload.get("target_platform", "unknown")},
                "detection": {"selection": {}, "condition": "selection"},
            }
        if "false_positive_analysis" in agent.output_schema.properties:
            output["false_positive_analysis"] = "False positives require environment-specific tuning."
        if "open_questions" in agent.output_schema.properties:
            output["open_questions"] = ["Connect a production model provider."]
        if "findings" in agent.output_schema.properties:
            output["findings"] = findings

        prompt_tokens = len(agent.role.split()) + len(agent.goal.split()) + len(str(input_payload).split())
        completion_tokens = len(str(output).split())
        token_usage = {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens}
        return ModelResponse(
            content=output,
            token_usage=token_usage,
            cost_estimate=_estimate_cost(token_usage),
            model=self.model,
        )


class OpenAIResponsesGateway:
    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise MissingModelProviderConfig("OPENAI_API_KEY is required for MODEL_PROVIDER=openai")
        self.settings = settings
        self.model = settings.default_model
        self.base_url = settings.openai_base_url.rstrip("/")

    def complete(
        self,
        agent: AgentContract,
        plan: ExecutionPlan,
        input_payload: dict[str, Any],
        findings: list[str],
    ) -> ModelResponse:
        messages = _build_prompt(agent, plan, input_payload, findings)
        payload = {
            "model": self.model,
            "input": messages,
            "temperature": self.settings.model_temperature,
            "max_output_tokens": self.settings.model_max_tokens,
        }
        try:
            response = httpx.post(
                f"{self.base_url}/responses",
                headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                json=payload,
                timeout=self.settings.model_timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise _http_error(exc, "OpenAI")
        data = response.json()
        text = data.get("output_text") or _response_output_text(data)
        usage = data.get("usage") or {}
        token_usage = {
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
        }
        return ModelResponse(
            content=_extract_json(text),
            token_usage=token_usage,
            cost_estimate=_estimate_cost(token_usage),
            model=data.get("model", self.model),
        )


def _response_output_text(data: dict[str, Any]) -> str:
    pieces: list[str] = []
    for output in data.get("output", []):
        for content in output.get("content", []):
            if isinstance(content, dict) and content.get("text"):
                pieces.append(content["text"])
    if not pieces:
        raise ModelGatewayError("OpenAI response did not include output text")
    return "\n".join(pieces)


class OpenAICompatibleChatGateway:
    def __init__(
        self,
        provider_name: str,
        base_url: str,
        api_key: str,
        model: str,
        settings: Settings,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        if not api_key:
            raise MissingModelProviderConfig(f"{provider_name} API key is required")
        self.provider_name = provider_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.settings = settings
        self.extra_headers = extra_headers or {}

    def complete(
        self,
        agent: AgentContract,
        plan: ExecutionPlan,
        input_payload: dict[str, Any],
        findings: list[str],
    ) -> ModelResponse:
        payload = {
            "model": self.model,
            "messages": _build_prompt(agent, plan, input_payload, findings),
            "temperature": self.settings.model_temperature,
            "max_tokens": self.settings.model_max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers,
        }
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.settings.model_timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise _http_error(exc, self.provider_name)
        data = response.json()
        choice = (data.get("choices") or [{}])[0]
        text = choice.get("message", {}).get("content")
        if not text:
            raise ModelGatewayError(f"{self.provider_name} response did not include message content")
        usage = data.get("usage") or {}
        token_usage = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
        }
        return ModelResponse(
            content=_extract_json(text),
            token_usage=token_usage,
            cost_estimate=_estimate_cost(token_usage),
            model=data.get("model", self.model),
        )


class OllamaChatGateway(OpenAICompatibleChatGateway):
    def __init__(self, settings: Settings) -> None:
        super().__init__(
            provider_name="Ollama",
            base_url=settings.ollama_base_url,
            api_key="ollama",
            model=settings.ollama_model,
            settings=settings,
        )


class AnthropicMessagesGateway:
    def __init__(self, settings: Settings) -> None:
        if not settings.anthropic_api_key:
            raise MissingModelProviderConfig("ANTHROPIC_API_KEY is required for MODEL_PROVIDER=anthropic")
        self.settings = settings
        self.model = settings.anthropic_model
        self.base_url = settings.anthropic_base_url.rstrip("/")

    def complete(
        self,
        agent: AgentContract,
        plan: ExecutionPlan,
        input_payload: dict[str, Any],
        findings: list[str],
    ) -> ModelResponse:
        messages = _build_prompt(agent, plan, input_payload, findings)
        payload = {
            "model": self.model,
            "max_tokens": self.settings.model_max_tokens,
            "temperature": self.settings.model_temperature,
            "system": messages[0]["content"],
            "messages": [{"role": "user", "content": messages[1]["content"]}],
        }
        try:
            response = httpx.post(
                f"{self.base_url}/v1/messages",
                headers={
                    "x-api-key": self.settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.settings.model_timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise _http_error(exc, "Anthropic")
        data = response.json()
        text = "\n".join(item.get("text", "") for item in data.get("content", []) if item.get("type") == "text")
        if not text:
            raise ModelGatewayError("Anthropic response did not include text content")
        usage = data.get("usage") or {}
        token_usage = {
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
        }
        return ModelResponse(
            content=_extract_json(text),
            token_usage=token_usage,
            cost_estimate=_estimate_cost(token_usage),
            model=data.get("model", self.model),
        )


class GeminiGenerateContentGateway:
    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key:
            raise MissingModelProviderConfig("GEMINI_API_KEY is required for MODEL_PROVIDER=gemini")
        self.settings = settings
        self.model = settings.gemini_model
        self.base_url = settings.gemini_base_url.rstrip("/")

    def complete(
        self,
        agent: AgentContract,
        plan: ExecutionPlan,
        input_payload: dict[str, Any],
        findings: list[str],
    ) -> ModelResponse:
        messages = _build_prompt(agent, plan, input_payload, findings)
        payload = {
            "systemInstruction": {"parts": [{"text": messages[0]["content"]}]},
            "contents": [{"role": "user", "parts": [{"text": messages[1]["content"]}]}],
            "generationConfig": {
                "temperature": self.settings.model_temperature,
                "maxOutputTokens": self.settings.model_max_tokens,
                "responseMimeType": "application/json",
            },
        }
        try:
            response = httpx.post(
                f"{self.base_url}/models/{self.model}:generateContent",
                headers={"x-goog-api-key": self.settings.gemini_api_key},
                json=payload,
                timeout=self.settings.model_timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise _http_error(exc, "Gemini")
        data = response.json()
        candidates = data.get("candidates") or []
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        text = "\n".join(part.get("text", "") for part in parts if part.get("text"))
        if not text:
            raise ModelGatewayError("Gemini response did not include text content")
        usage = data.get("usageMetadata") or {}
        token_usage = {
            "prompt_tokens": usage.get("promptTokenCount", 0),
            "completion_tokens": usage.get("candidatesTokenCount", 0),
        }
        return ModelResponse(
            content=_extract_json(text),
            token_usage=token_usage,
            cost_estimate=_estimate_cost(token_usage),
            model=self.model,
        )


def get_model_gateway(settings: Settings | None = None) -> ModelGateway:
    settings = settings or get_settings()
    provider = settings.model_provider.lower()
    if provider == "stub":
        return StubModelGateway()
    if provider in {"openai", "chatgpt"}:
        return OpenAIResponsesGateway(settings)
    if provider == "openrouter":
        return OpenAICompatibleChatGateway(
            provider_name="OpenRouter",
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            settings=settings,
        )
    if provider in {"anthropic", "claude"}:
        return AnthropicMessagesGateway(settings)
    if provider == "gemini":
        return GeminiGenerateContentGateway(settings)
    if provider == "ollama":
        return OllamaChatGateway(settings)
    raise MissingModelProviderConfig(f"Unsupported MODEL_PROVIDER={settings.model_provider}")


def model_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    provider = settings.model_provider.lower()
    model_by_provider = {
        "stub": "stub-model",
        "openai": settings.default_model,
        "chatgpt": settings.default_model,
        "openrouter": settings.openrouter_model,
        "anthropic": settings.anthropic_model,
        "claude": settings.anthropic_model,
        "gemini": settings.gemini_model,
        "ollama": settings.ollama_model,
    }
    key_status = {
        "stub": "not_required",
        "openai": "configured" if settings.openai_api_key else "missing_key",
        "chatgpt": "configured" if settings.openai_api_key else "missing_key",
        "openrouter": "configured" if settings.openrouter_api_key else "missing_key",
        "anthropic": "configured" if settings.anthropic_api_key else "missing_key",
        "claude": "configured" if settings.anthropic_api_key else "missing_key",
        "gemini": "configured" if settings.gemini_api_key else "missing_key",
        "ollama": "not_required",
    }
    status = {
        "provider": settings.model_provider,
        "model": model_by_provider.get(provider, settings.default_model),
        "api_key": key_status.get(provider, "unknown_provider"),
        "timeout_seconds": settings.model_timeout_seconds,
    }
    if provider == "ollama":
        status["base_url"] = settings.ollama_base_url
        status["ollama"] = _ollama_status(settings)
    return status


def _ollama_status(settings: Settings) -> str:
    try:
        response = httpx.get(
            f"{settings.ollama_base_url.rstrip('/')}/models",
            timeout=min(settings.model_timeout_seconds, 3),
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return "unreachable"
    return "reachable"


def build_provider_payload_for_test(
    provider: str,
    agent: AgentContract,
    plan: ExecutionPlan,
    input_payload: dict[str, Any],
    findings: list[str],
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    messages = _build_prompt(agent, plan, input_payload, findings)
    if provider == "openai":
        return {"model": settings.default_model, "input": messages}
    if provider in {"openrouter", "ollama"}:
        model = settings.openrouter_model if provider == "openrouter" else settings.ollama_model
        return {"model": model, "messages": messages, "temperature": settings.model_temperature}
    if provider == "anthropic":
        return {"model": settings.anthropic_model, "system": messages[0]["content"], "messages": [messages[1]]}
    if provider == "gemini":
        return {"contents": [{"role": "user", "parts": [{"text": messages[1]["content"]}]}]}
    raise ValueError(provider)
