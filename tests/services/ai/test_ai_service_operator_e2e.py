from types import SimpleNamespace

from atlas.services.ai.models import AIRequest
from atlas.services.ai.service import AIService


class FakeProvider:

    def __init__(
        self,
        response="structured reasoning response",
        available=True,
        fail=False,
        fail_models=None,
    ):
        self.response = response
        self._available = available
        self.fail = fail
        self.fail_models = set(fail_models or [])
        self.calls = []

    def available(self):
        return self._available

    def generate(
        self,
        prompt,
        model,
        temperature=None,
        max_tokens=None,
        keep_alive=None,
    ):
        self.calls.append(
            {
                "prompt": prompt,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "keep_alive": keep_alive,
            }
        )

        if self.fail or model in self.fail_models:
            raise RuntimeError(
                "primary generation failed"
            )

        return self.response


class FakeRuntime:

    def __init__(self, states):
        self.states = states
        self.events = []

    def status(self):
        return self.states

    def load(self, model):
        self.events.append(
            ("load", model)
        )

    def unload(self, model):
        self.events.append(
            ("unload", model)
        )

    def unload_all(self):
        self.events.append(
            ("unload_all",)
        )

    def record_request(self, model):
        self.events.append(
            ("request", model)
        )

    def record_success(self, model, latency):
        self.events.append(
            ("success", model)
        )

    def record_failure(self, model, error):
        self.events.append(
            ("failure", model, error)
        )


def runtime_state(
    model,
    installed=True,
):
    return SimpleNamespace(
        model=model,
        installed=installed,
    )


def build_service(
    primary_fail=False,
):

    service = AIService.__new__(
        AIService
    )

    service.providers = {}

    service.runtime_target = SimpleNamespace(
        provider="ollama",
    )

    service.runtime = FakeRuntime(
        [
            runtime_state(
                "qwen_reasoning_9b",
                True,
            ),
            runtime_state(
                "qwen_summary",
                True,
            ),
            runtime_state(
                "qwen_coder",
                True,
            ),
            runtime_state(
                "qwen_reasoning_14b",
                True,
            ),
            runtime_state(
                "qwen_summary_14b",
                True,
            ),
        ]
    )

    service.operator = __import__(
        "atlas.services.ai.operator.operator",
        fromlist=["AIModelOperator"],
    ).AIModelOperator()

    from atlas.services.ai.operator.execution_service import (
        OperatorExecutionService,
    )

    service.execution_service = OperatorExecutionService(
        service.operator
    )

    provider = FakeProvider(
        fail=primary_fail,
        response=(
            "root_cause: DNS failure\n"
            "confidence: 0.95\n"
            "evidence: jellyseerr DNS resolution failed"
        ),
    )

    service.providers["ollama"] = provider

    service.reasoning_gate = SimpleNamespace(
        evaluate=lambda result, task: SimpleNamespace(
            escalate=False,
            reasons=[],
        )
    )

    return service, provider


def test_ai_service_ask_executes_primary_model():

    service, provider = build_service(
        primary_fail=False
    )

    request = AIRequest(
        task="incident_reasoning",
        user_prompt="Analyze the Jellyseerr DNS failure.",
    )

    response = service.ask(
        request
    )

    assert response.model == "qwen_reasoning_9b"

    assert response.provider == "ollama"

    assert response.content

    assert response.metadata["fallback"] is False

    assert (
        response.metadata["primary_model"]
        == "qwen_reasoning_9b"
    )

    # Primary execution must call the 7B exactly once.
    assert len(provider.calls) == 1

    assert (
        provider.calls[0]["model"]
        == "qwen3.5:9b"
    )

    assert (
        provider.calls[0]["keep_alive"]
        == 0
    )

    assert (
        ("load", "qwen_reasoning_9b")
        in service.runtime.events
    )

    assert (
        ("request", "qwen_reasoning_9b")
        in service.runtime.events
    )

    assert (
        ("success", "qwen_reasoning_9b")
        in service.runtime.events
    )

    assert (
        ("unload_all",)
        in service.runtime.events
    )


def test_ai_service_ask_falls_back_after_primary_failure():

    service, provider = build_service(
        primary_fail=False
    )

    # Force only the primary 7B model to fail.
    provider.fail_models.add(
        "qwen3.5:9b"
    )

    request = AIRequest(
        task="incident_reasoning",
        user_prompt="Analyze the Jellyseerr DNS failure.",
    )

    response = service.ask(
        request
    )

    assert response.model == "qwen_reasoning_14b"

    assert response.provider == "ollama"

    assert response.content

    assert response.metadata["fallback"] is True

    assert (
        response.metadata["primary_model"]
        == "qwen_reasoning_9b"
    )

    assert (
        response.metadata["fallback_model"]
        == "qwen_reasoning_14b"
    )

    # Same provider is intentionally used for both models.
    # The important distinction is the provider model.
    assert len(provider.calls) == 2

    assert (
        provider.calls[0]["model"]
        == "qwen3.5:9b"
    )

    assert (
        provider.calls[1]["model"]
        == "qwen2.5:14b"
    )

    assert (
        provider.calls[0]["keep_alive"]
        == 0
    )

    assert (
        provider.calls[1]["keep_alive"]
        == 0
    )

    # Primary must be explicitly unloaded before fallback.
    assert (
        ("unload", "qwen_reasoning_9b")
        in service.runtime.events
    )

    assert (
        ("load", "qwen_reasoning_14b")
        in service.runtime.events
    )

    assert (
        ("request", "qwen_reasoning_14b")
        in service.runtime.events
    )

    assert (
        ("success", "qwen_reasoning_14b")
        in service.runtime.events
    )

    assert (
        ("unload_all",)
        in service.runtime.events
    )


def test_ai_service_ask_reports_unavailable_model():

    service, _ = build_service()

    service.runtime.states = [
        runtime_state(
            "qwen_reasoning_9b",
            False,
        ),
        runtime_state(
            "qwen_reasoning_14b",
            False,
        ),
    ]

    request = AIRequest(
        task="incident_reasoning",
        user_prompt="Analyze the incident.",
    )

    response = service.ask(
        request
    )

    assert response.model == "qwen_reasoning_9b"

    assert response.provider == "ollama"

    assert (
        response.metadata["reason"]
        == "model_not_installed"
    )

    assert (
        response.metadata["provider_model"]
        == "qwen3.5:9b"
    )

    assert (
        response.metadata["task"]
        == "incident_reasoning"
    )
