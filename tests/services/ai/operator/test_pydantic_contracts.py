import pytest
from pydantic import ValidationError

from atlas.services.ai.operator.models import (
    AIModelCapabilities,
    AIModelProfile,
)


def test_model_profile_is_pydantic_contract():

    profile = AIModelProfile(
        name="qwen_reasoning",
        provider="ollama",
        provider_model="qwen2.5:7b",
        capabilities=AIModelCapabilities(
            reasoning=True,
            context_window=32768,
            parameter_size="7B",
        ),
    )

    assert profile.name == "qwen_reasoning"
    assert profile.capabilities.reasoning is True

    dumped = profile.model_dump()

    assert dumped["provider"] == "ollama"
    assert dumped["capabilities"]["context_window"] == 32768


def test_capabilities_reject_invalid_context_window():

    with pytest.raises(ValidationError):
        AIModelCapabilities(
            context_window=0,
        )


def test_profile_rejects_negative_priority():

    with pytest.raises(ValidationError):
        AIModelProfile(
            name="test",
            provider="ollama",
            provider_model="test:7b",
            capabilities=AIModelCapabilities(),
            priority=-1,
        )


def test_profile_rejects_empty_name():

    with pytest.raises(ValidationError):
        AIModelProfile(
            name="",
            provider="ollama",
            provider_model="test:7b",
            capabilities=AIModelCapabilities(),
        )


def test_profile_rejects_unknown_fields():

    with pytest.raises(ValidationError):
        AIModelProfile(
            name="test",
            provider="ollama",
            provider_model="test:7b",
            capabilities=AIModelCapabilities(),
            unexpected="value",
        )


def test_profile_rejects_self_fallback():

    with pytest.raises(ValidationError):
        AIModelProfile(
            name="qwen_reasoning",
            provider="ollama",
            provider_model="qwen2.5:7b",
            capabilities=AIModelCapabilities(
                reasoning=True,
            ),
            fallback_for="qwen_reasoning",
        )


def test_nested_capabilities_are_validated():

    profile = AIModelProfile(
        name="qwen_reasoning_14b",
        provider="ollama",
        provider_model="qwen2.5:14b",
        capabilities={
            "reasoning": True,
            "summary": True,
            "context_window": 32768,
            "parameter_size": "14B",
        },
        priority=200,
        fallback_for="qwen_reasoning",
    )

    assert isinstance(
        profile.capabilities,
        AIModelCapabilities,
    )

    assert profile.priority == 200
    assert profile.fallback_for == "qwen_reasoning"
