import pytest

from atlas.services.ai.llm.ollama import OllamaProvider
from atlas.services.ai.models import AIRequest
from atlas.services.ai.service import AIService


INSTALLED_MODELS = [
    "qwen3.5:9b",
    "qwen2.5:7b",
    "qwen2.5-coder:7b",
    "qwen2.5:14b",
]


@pytest.fixture(
    autouse=True,
)
def deterministic_ollama_inventory(
    monkeypatch,
):
    """
    Model-routing tests must not depend on a live Ollama
    instance or on a machine-specific network endpoint.
    """

    monkeypatch.setattr(
        OllamaProvider,
        "models",
        lambda self: list(
            INSTALLED_MODELS
        ),
    )


def test_coding_task_selects_coder_model():

    ai = AIService()

    model = ai.operator.select(
        "coding",
        ai.runtime,
    )

    assert model is not None
    assert model.name == "qwen_coder"
    assert model.provider_model == "qwen2.5-coder:7b"


def test_development_task_selects_coder_model():

    ai = AIService()

    model = ai.operator.select(
        "development",
        ai.runtime,
    )

    assert model is not None
    assert model.name == "qwen_coder"


def test_code_review_task_selects_coder_model():

    ai = AIService()

    model = ai.operator.select(
        "code_review",
        ai.runtime,
    )

    assert model is not None
    assert model.name == "qwen_coder"


def test_reasoning_does_not_select_coder():

    ai = AIService()

    model = ai.operator.select(
        "reasoning",
        ai.runtime,
    )

    assert model is not None
    assert model.name == "qwen_reasoning_9b"
    assert model.name != "qwen_coder"


def test_coding_model_runtime_is_installed():

    ai = AIService()

    state = next(
        item
        for item in ai.runtime.status()
        if item.model == "qwen_coder"
    )

    assert state.installed is True


def test_coding_model_is_not_loaded_initially():

    ai = AIService()

    state = next(
        item
        for item in ai.runtime.status()
        if item.model == "qwen_coder"
    )

    assert state.loaded is False
