import pytest
from pydantic import ValidationError

from atlas.services.ai.models import (
    AIRequest,
    LLMResponse,
)


def test_ai_request_is_pydantic_contract():

    request = AIRequest(
        task="incident_reasoning",
        user_prompt="Analyze the DNS failure.",
    )

    assert request.task == "incident_reasoning"
    assert request.user_prompt == "Analyze the DNS failure."
    assert request.priority == "normal"
    assert request.context_required is True
    assert request.max_tokens == 2048
    assert request.temperature == 0.2


def test_ai_request_serializes_cleanly():

    request = AIRequest(
        task="diagnosis",
        user_prompt="Analyze incident.",
        priority="high",
        context_required=False,
        max_tokens=4096,
        temperature=0.5,
    )

    assert request.model_dump() == {
        "task": "diagnosis",
        "user_prompt": "Analyze incident.",
        "priority": "high",
        "context_required": False,
        "max_tokens": 4096,
        "temperature": 0.5,
    }


def test_ai_request_rejects_empty_task():

    with pytest.raises(ValidationError):
        AIRequest(
            task="",
            user_prompt="Analyze incident.",
        )


def test_ai_request_rejects_empty_prompt():

    with pytest.raises(ValidationError):
        AIRequest(
            task="diagnosis",
            user_prompt="",
        )


def test_ai_request_rejects_invalid_max_tokens():

    with pytest.raises(ValidationError):
        AIRequest(
            task="diagnosis",
            user_prompt="Analyze incident.",
            max_tokens=0,
        )


def test_ai_request_rejects_invalid_temperature():

    with pytest.raises(ValidationError):
        AIRequest(
            task="diagnosis",
            user_prompt="Analyze incident.",
            temperature=-0.1,
        )

    with pytest.raises(ValidationError):
        AIRequest(
            task="diagnosis",
            user_prompt="Analyze incident.",
            temperature=2.1,
        )


def test_ai_request_rejects_unknown_fields():

    with pytest.raises(ValidationError):
        AIRequest(
            task="diagnosis",
            user_prompt="Analyze incident.",
            unexpected="value",
        )


def test_ai_request_assignment_is_validated():

    request = AIRequest(
        task="diagnosis",
        user_prompt="Analyze incident.",
    )

    with pytest.raises(ValidationError):
        request.max_tokens = 0


def test_llm_response_is_pydantic_contract():

    response = LLMResponse(
        model="qwen_reasoning",
        provider="ollama",
        content="DNS failure detected.",
    )

    assert response.model == "qwen_reasoning"
    assert response.provider == "ollama"
    assert response.content == "DNS failure detected."
    assert response.latency_ms == 0
    assert response.tokens == 0
    assert response.metadata == {}


def test_llm_response_serializes_cleanly():

    response = LLMResponse(
        model="qwen_reasoning_14b",
        provider="ollama",
        content="Root cause identified.",
        latency_ms=123.4,
        tokens=512,
        metadata={
            "fallback": True,
            "primary_model": "qwen_reasoning",
        },
    )

    assert response.model_dump() == {
        "model": "qwen_reasoning_14b",
        "provider": "ollama",
        "content": "Root cause identified.",
        "latency_ms": 123.4,
        "tokens": 512,
        "metadata": {
            "fallback": True,
            "primary_model": "qwen_reasoning",
        },
    }


def test_llm_response_rejects_empty_model():

    with pytest.raises(ValidationError):
        LLMResponse(
            model="",
            provider="ollama",
            content="response",
        )


def test_llm_response_rejects_empty_provider():

    with pytest.raises(ValidationError):
        LLMResponse(
            model="qwen_reasoning",
            provider="",
            content="response",
        )


def test_llm_response_rejects_negative_latency():

    with pytest.raises(ValidationError):
        LLMResponse(
            model="qwen_reasoning",
            provider="ollama",
            content="response",
            latency_ms=-1,
        )


def test_llm_response_rejects_negative_tokens():

    with pytest.raises(ValidationError):
        LLMResponse(
            model="qwen_reasoning",
            provider="ollama",
            content="response",
            tokens=-1,
        )


def test_llm_response_rejects_unknown_fields():

    with pytest.raises(ValidationError):
        LLMResponse(
            model="qwen_reasoning",
            provider="ollama",
            content="response",
            unexpected="value",
        )


def test_llm_response_assignment_is_validated():

    response = LLMResponse(
        model="qwen_reasoning",
        provider="ollama",
        content="response",
    )

    with pytest.raises(ValidationError):
        response.tokens = -1
