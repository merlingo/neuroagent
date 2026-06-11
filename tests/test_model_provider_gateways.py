import httpx
import pytest

from app.contracts.workflow_contract import ExecutionPlan
from app.domains.registry import DomainRegistry
from app.model_gateway import (
    AnthropicMessagesGateway,
    GeminiGenerateContentGateway,
    MissingModelProviderConfig,
    OpenAICompatibleChatGateway,
    OpenAIResponsesGateway,
    OllamaChatGateway,
    StubModelGateway,
    build_provider_payload_for_test,
    get_model_gateway,
    model_status,
)
from app.settings import Settings


def _agent_and_plan():
    agent = DomainRegistry.from_default_path().get_agent("research.literature_researcher")
    return agent, ExecutionPlan(
        intent="test",
        domain=agent.domain,
        agent_id=agent.agent_id,
        steps=[],
    )


def _response(url: str, payload: dict) -> httpx.Response:
    return httpx.Response(200, json=payload, request=httpx.Request("POST", url))


def test_model_gateway_factory_selects_configured_provider() -> None:
    assert isinstance(get_model_gateway(Settings(model_provider="stub")), StubModelGateway)
    assert isinstance(
        get_model_gateway(Settings(model_provider="openai", openai_api_key="key")),
        OpenAIResponsesGateway,
    )
    assert isinstance(
        get_model_gateway(Settings(model_provider="openrouter", openrouter_api_key="key")),
        OpenAICompatibleChatGateway,
    )
    assert isinstance(
        get_model_gateway(Settings(model_provider="anthropic", anthropic_api_key="key")),
        AnthropicMessagesGateway,
    )
    assert isinstance(
        get_model_gateway(Settings(model_provider="gemini", gemini_api_key="key")),
        GeminiGenerateContentGateway,
    )
    assert isinstance(get_model_gateway(Settings(model_provider="ollama")), OllamaChatGateway)


def test_remote_provider_requires_api_key() -> None:
    with pytest.raises(MissingModelProviderConfig, match="OPENAI_API_KEY"):
        get_model_gateway(Settings(model_provider="openai", openai_api_key=""))


def test_provider_payload_shapes_include_model_and_messages() -> None:
    agent, plan = _agent_and_plan()
    settings = Settings(
        default_model="gpt-test",
        openrouter_model="openrouter-test",
        anthropic_model="claude-test",
        gemini_model="gemini-test",
        ollama_model="ollama-test",
    )

    assert build_provider_payload_for_test("openai", agent, plan, {}, [], settings)["model"] == "gpt-test"
    assert build_provider_payload_for_test("openrouter", agent, plan, {}, [], settings)["messages"]
    assert build_provider_payload_for_test("ollama", agent, plan, {}, [], settings)["model"] == "ollama-test"
    assert build_provider_payload_for_test("anthropic", agent, plan, {}, [], settings)["system"]
    assert build_provider_payload_for_test("gemini", agent, plan, {}, [], settings)["contents"]


def test_openai_responses_gateway_parses_json_output(monkeypatch) -> None:
    agent, plan = _agent_and_plan()
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return _response(
            url,
            {
                "model": "gpt-test",
                "output_text": '{"summary":"ok","evidence":[],"confidence_score":0.8}',
                "usage": {"input_tokens": 10, "output_tokens": 5},
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    result = OpenAIResponsesGateway(
        Settings(openai_api_key="key", default_model="gpt-test")
    ).complete(agent, plan, {"research_question": "x"}, [])

    assert captured["url"].endswith("/responses")
    assert captured["json"]["input"]
    assert result.content["summary"] == "ok"
    assert result.token_usage == {"prompt_tokens": 10, "completion_tokens": 5}


def test_openai_compatible_gateway_parses_chat_completion(monkeypatch) -> None:
    agent, plan = _agent_and_plan()
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return _response(
            url,
            {
                "model": "router-test",
                "choices": [
                    {"message": {"content": '{"summary":"ok","evidence":[],"confidence_score":0.7}'}}
                ],
                "usage": {"prompt_tokens": 4, "completion_tokens": 3},
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    result = OpenAICompatibleChatGateway(
        "OpenRouter",
        "https://openrouter.ai/api/v1",
        "key",
        "router-test",
        Settings(),
    ).complete(agent, plan, {"research_question": "x"}, [])

    assert captured["url"].endswith("/chat/completions")
    assert captured["json"]["messages"]
    assert result.content["confidence_score"] == 0.7


def test_anthropic_and_gemini_payloads_parse_text(monkeypatch) -> None:
    agent, plan = _agent_and_plan()
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append((url, json))
        if url.endswith("/v1/messages"):
            return _response(
                url,
                {
                    "model": "claude-test",
                    "content": [
                        {"type": "text", "text": '{"summary":"claude","evidence":[],"confidence_score":0.6}'}
                    ],
                    "usage": {"input_tokens": 7, "output_tokens": 8},
                },
            )
        return _response(
            url,
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": '{"summary":"gemini","evidence":[],"confidence_score":0.65}'}
                            ]
                        }
                    }
                ],
                "usageMetadata": {"promptTokenCount": 6, "candidatesTokenCount": 9},
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    claude = AnthropicMessagesGateway(
        Settings(anthropic_api_key="key", anthropic_model="claude-test")
    ).complete(agent, plan, {"research_question": "x"}, [])
    gemini = GeminiGenerateContentGateway(
        Settings(gemini_api_key="key", gemini_model="gemini-test")
    ).complete(agent, plan, {"research_question": "x"}, [])

    assert claude.content["summary"] == "claude"
    assert gemini.content["summary"] == "gemini"
    assert calls[0][1]["messages"][0]["role"] == "user"
    assert calls[1][1]["contents"][0]["parts"]


def test_model_status_reports_stub_without_network() -> None:
    assert model_status(Settings(model_provider="stub")) == {
        "provider": "stub",
        "model": "stub-model",
        "api_key": "not_required",
        "timeout_seconds": 60,
    }
