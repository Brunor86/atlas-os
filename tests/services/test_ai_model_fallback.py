from unittest.mock import Mock

from atlas.services.ai.models import AIRequest
from atlas.services.ai.service import AIService


def _service_with_models(
    *,
    primary_installed=True,
    fallback_installed=True,
):
    service = AIService()

    service.runtime.mark_installed(
        "qwen_reasoning_9b",
        primary_installed,
    )

    service.runtime.mark_installed(
        "qwen_reasoning_14b",
        fallback_installed,
    )

    provider = Mock()

    provider.available.return_value = True

    service.providers["ollama"] = provider

    return service, provider


def test_primary_7b_success_does_not_use_fallback():
    service, provider = _service_with_models(
        primary_installed=True,
        fallback_installed=True,
    )

    provider.generate_with_tools.return_value = {
        "message": {
            "content": "primary response",
            "tool_calls": [],
        }
    }

    response = service.ask(
        AIRequest(
            task="incident_reasoning",
            user_prompt="test",
        )
    )

    assert response.model == "qwen_reasoning_9b"

    assert response.metadata["fallback"] is False

    provider.generate_with_tools.assert_called_once()

    call = provider.generate_with_tools.call_args

    assert call.kwargs["model"] == "qwen3.5:9b"

    assert call.kwargs["keep_alive"] == 0

    assert not service.runtime.models[
        "qwen_reasoning_9b"
    ].loaded

    assert not service.runtime.models[
        "qwen_reasoning_14b"
    ].loaded


def test_primary_failure_uses_14b_fallback():
    service, provider = _service_with_models(
        primary_installed=True,
        fallback_installed=True,
    )

    provider.generate_with_tools.side_effect = [
        RuntimeError("7B failure"),
        {
            "message": {
                "content": "14B response",
                "tool_calls": [],
            }
        },
    ]

    response = service.ask(
        AIRequest(
            task="incident_reasoning",
            user_prompt="test",
        )
    )

    assert response.model == "qwen_reasoning_14b"

    assert response.metadata["fallback"] is True

    assert (
        response.metadata["primary_model"]
        == "qwen_reasoning_9b"
    )

    assert (
        response.metadata["fallback_model"]
        == "qwen_reasoning_14b"
    )

    assert provider.generate_with_tools.call_count == 2

    calls = provider.generate_with_tools.call_args_list

    assert (
        calls[0].kwargs["model"]
        == "qwen3.5:9b"
    )

    assert calls[0].kwargs["keep_alive"] == 0

    assert (
        calls[1].kwargs["model"]
        == "qwen2.5:14b"
    )

    assert calls[1].kwargs["keep_alive"] == 0

    assert not service.runtime.models[
        "qwen_reasoning_9b"
    ].loaded

    assert not service.runtime.models[
        "qwen_reasoning_14b"
    ].loaded


def test_primary_failure_without_installed_fallback():
    service, provider = _service_with_models(
        primary_installed=True,
        fallback_installed=False,
    )

    provider.generate_with_tools.side_effect = RuntimeError(
        "7B failure"
    )

    response = service.ask(
        AIRequest(
            task="incident_reasoning",
            user_prompt="test",
        )
    )

    assert response.model == "qwen_reasoning_9b"

    assert response.metadata["fallback"] is False

    assert (
        "no fallback model"
        in response.content
    )

    assert provider.generate_with_tools.call_count == 1

    assert not service.runtime.models[
        "qwen_reasoning_9b"
    ].loaded


def test_primary_and_fallback_failure_release_runtime():
    service, provider = _service_with_models(
        primary_installed=True,
        fallback_installed=True,
    )

    provider.generate_with_tools.side_effect = [
        RuntimeError("7B failure"),
        RuntimeError("14B failure"),
    ]

    response = service.ask(
        AIRequest(
            task="incident_reasoning",
            user_prompt="test",
        )
    )

    assert response.metadata["fallback"] is True

    assert (
        "all fallback models failed"
        in response.content
    )

    assert provider.generate_with_tools.call_count == 2

    calls = provider.generate_with_tools.call_args_list

    assert (
        calls[0].kwargs["model"]
        == "qwen3.5:9b"
    )

    assert (
        calls[1].kwargs["model"]
        == "qwen2.5:14b"
    )

    assert (
        calls[0].kwargs["keep_alive"]
        == 0
    )

    assert (
        calls[1].kwargs["keep_alive"]
        == 0
    )

    for state in service.runtime.status():

        assert state.loaded is False


def test_14b_is_never_selected_as_primary():
    service, _ = _service_with_models(
        primary_installed=True,
        fallback_installed=True,
    )

    selected = service.operator.select(
        "incident_reasoning",
        service.runtime,
    )

    assert selected is not None

    assert selected.name == "qwen_reasoning_9b"

    assert selected.provider_model == "qwen3.5:9b"


def test_reasoning_fallback_chain_points_to_14b():
    service, _ = _service_with_models(
        primary_installed=True,
        fallback_installed=True,
    )

    primary = next(
        model
        for model in service.operator.list_models()
        if model.name == "qwen_reasoning_9b"
    )

    fallbacks = service.operator.fallback_candidates(
        primary,
        service.runtime,
    )

    assert [
        model.name
        for model in fallbacks
    ] == [
        "qwen_reasoning_14b",
    ]


def test_summary_7b_uses_summary_14b_fallback():
    service = AIService()

    service.runtime.mark_installed(
        "qwen_summary",
        True,
    )

    service.runtime.mark_installed(
        "qwen_summary_14b",
        True,
    )

    provider = Mock()

    provider.available.return_value = True

    provider.generate_with_tools.side_effect = [
        RuntimeError("summary 7B failure"),
        {
            "message": {
                "content": "summary 14B response",
                "tool_calls": [],
            }
        },
    ]

    service.providers["ollama"] = provider

    response = service.ask(
        AIRequest(
            task="summary",
            user_prompt="summarize this",
        )
    )

    assert response.model == "qwen_summary_14b"

    assert response.metadata["fallback"] is True

    assert (
        response.metadata["primary_model"]
        == "qwen_summary"
    )

    assert (
        response.metadata["fallback_model"]
        == "qwen_summary_14b"
    )

    calls = provider.generate_with_tools.call_args_list

    assert (
        calls[0].kwargs["model"]
        == "qwen2.5:7b"
    )

    assert (
        calls[1].kwargs["model"]
        == "qwen2.5:14b"
    )

    assert calls[0].kwargs["keep_alive"] == 0

    assert calls[1].kwargs["keep_alive"] == 0

    for state in service.runtime.status():
        assert state.loaded is False


def test_fallback_is_unavailable_when_14b_is_not_installed():
    service, _ = _service_with_models(
        primary_installed=True,
        fallback_installed=False,
    )

    primary = next(
        model
        for model in service.operator.list_models()
        if model.name == "qwen_reasoning_9b"
    )

    fallbacks = service.operator.fallback_candidates(
        primary,
        service.runtime,
    )

    assert fallbacks == []


def test_primary_7b_low_quality_reasoning_uses_14b_fallback():
    service, provider = _service_with_models(
        primary_installed=True,
        fallback_installed=True,
    )

    provider.generate_with_tools.side_effect = [
        {
            "message": {
                "content": (
                    '{"summary": "Application offline",'
                    '"root_cause": "unknown",'
                    '"evidence": ["application offline"],'
                    '"missing_evidence": ["container logs"],'
                    '"confidence": 0.5}'
                ),
                "tool_calls": [],
            }
        },
        {
            "message": {
                "content": (
                    '{"summary": "Application offline",'
                    '"root_cause": "container stopped",'
                    '"evidence": ["container stopped"],'
                    '"missing_evidence": [],'
                    '"confidence": 0.95}'
                ),
                "tool_calls": [],
            }
        },
    ]

    response = service.ask(
        AIRequest(
            task="incident_reasoning",
            user_prompt="diagnose incident",
        )
    )

    assert response.model == "qwen_reasoning_14b"

    assert response.metadata["fallback"] is True

    assert (
        response.metadata["primary_model"]
        == "qwen_reasoning_9b"
    )

    assert (
        response.metadata["fallback_model"]
        == "qwen_reasoning_14b"
    )

    assert (
        response.metadata["fallback_reason"]
        == "reasoning_gate"
    )

    gate = response.metadata["reasoning_gate"]

    assert gate["escalate"] is True

    assert gate["score"] < 0.70

    assert (
        "low model confidence"
        in gate["reasons"]
    )

    assert (
        "missing evidence reported"
        in gate["reasons"]
    )

    assert provider.generate_with_tools.call_count == 2

    calls = provider.generate_with_tools.call_args_list

    assert (
        calls[0].kwargs["model"]
        == "qwen3.5:9b"
    )

    assert (
        calls[1].kwargs["model"]
        == "qwen2.5:14b"
    )

    assert (
        calls[0].kwargs["keep_alive"]
        == 0
    )

    assert (
        calls[1].kwargs["keep_alive"]
        == 0
    )

    for state in service.runtime.status():
        assert state.loaded is False


def test_primary_7b_good_reasoning_does_not_escalate():
    service, provider = _service_with_models(
        primary_installed=True,
        fallback_installed=True,
    )

    provider.generate_with_tools.return_value = {
        "message": {
            "content": (
                '{"summary": "Reverse proxy unavailable",'
                '"root_cause": "container stopped",'
                '"evidence": ['
                '"container stopped",'
                '"application status OFFLINE"'
                '],'
                '"missing_evidence": [],'
                '"confidence": 0.95}'
            ),
            "tool_calls": [],
        }
    }

    response = service.ask(
        AIRequest(
            task="incident_reasoning",
            user_prompt="diagnose incident",
        )
    )

    assert response.model == "qwen_reasoning_9b"

    assert response.metadata["fallback"] is False

    assert (
        response.metadata["primary_model"]
        == "qwen_reasoning_9b"
    )

    assert "fallback_reason" not in response.metadata

    assert "reasoning_gate" not in response.metadata

    provider.generate_with_tools.assert_called_once()

    call = provider.generate_with_tools.call_args

    assert (
        call.kwargs["model"]
        == "qwen3.5:9b"
    )

    assert (
        call.kwargs["keep_alive"]
        == 0
    )

    for state in service.runtime.status():
        assert state.loaded is False


def test_fallback_14b_good_reasoning_passes_reasoning_gate():
    service, provider = _service_with_models(
        primary_installed=True,
        fallback_installed=True,
    )

    provider.generate_with_tools.side_effect = [
        {
            "message": {
                "content": (
                    '{"summary": "Application offline",'
                    '"root_cause": "unknown",'
                    '"evidence": ["application offline"],'
                    '"missing_evidence": ["container logs"],'
                    '"confidence": 0.5}'
                ),
                "tool_calls": [],
            }
        },
        {
            "message": {
                "content": (
                    '{"summary": "Application offline",'
                    '"root_cause": "container stopped",'
                    '"evidence": ["container stopped"],'
                    '"missing_evidence": [],'
                    '"confidence": 0.95}'
                ),
                "tool_calls": [],
            }
        },
    ]

    response = service.ask(
        AIRequest(
            task="incident_reasoning",
            user_prompt="diagnose incident",
        )
    )

    assert response.model == "qwen_reasoning_14b"
    assert response.metadata["fallback"] is True
    assert response.content

    assert (
        response.metadata["fallback_reason"]
        == "reasoning_gate"
    )


def test_fallback_14b_low_quality_reasoning_is_rejected():
    service, provider = _service_with_models(
        primary_installed=True,
        fallback_installed=True,
    )

    provider.generate_with_tools.side_effect = [
        (
            '{"summary": "Application offline",'
            '"root_cause": "unknown",'
            '"evidence": ["application offline"],'
            '"missing_evidence": ["container logs"],'
            '"confidence": 0.5}'
        ),
        (
            '{"summary": "Application offline",'
            '"root_cause": "unknown",'
            '"evidence": ["application offline"],'
            '"missing_evidence": ["container logs"],'
            '"confidence": 0.5}'
        ),
    ]

    response = service.ask(
        AIRequest(
            task="incident_reasoning",
            user_prompt="diagnose incident",
        )
    )

    assert response.model == "qwen_reasoning_9b"

    assert (
        response.content
        == "Primary AI model failed and all fallback models failed."
    )

    assert response.metadata["fallback"] is True
    assert response.metadata["error"]

    assert provider.generate_with_tools.call_count == 2
