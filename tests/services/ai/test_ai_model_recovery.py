from atlas.services.ai.operator.operator import AIModelOperator
from atlas.services.ai.runtime import AIModelRuntime
from atlas.services.ai.service import AIService


class RecoveringDiscovery:

    def __init__(self, runtime):
        self.runtime = runtime
        self.calls = 0

    def scan(self):
        self.calls += 1

        self.runtime.mark_installed(
            "qwen_reasoning_9b",
            True,
        )

        return []


def test_model_selection_recovers_after_provider_returns():

    service = AIService.__new__(
        AIService
    )

    service.operator = AIModelOperator()
    service.runtime = AIModelRuntime()

    service.operator.register_runtime(
        service.runtime
    )

    service.discovery = RecoveringDiscovery(
        service.runtime
    )

    # Simulate AIService having started while Ollama was offline.
    assert (
        service.operator.select(
            "reasoning",
            service.runtime,
        )
        is None
    )

    # Ollama has returned. The first selection miss must trigger
    # exactly one availability refresh and recover automatically.
    model = service._select_model_with_refresh(
        "reasoning"
    )

    assert model is not None
    assert model.name == "qwen_reasoning_9b"
    assert model.provider_model == "qwen3.5:9b"
    assert service.discovery.calls == 1

    # Once healthy, model selection must use the normal fast path
    # without another provider scan.
    model = service._select_model_with_refresh(
        "reasoning"
    )

    assert model is not None
    assert model.name == "qwen_reasoning_9b"
    assert service.discovery.calls == 1
