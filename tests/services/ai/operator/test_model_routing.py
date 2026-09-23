from dataclasses import dataclass

from atlas.services.ai.operator.operator import AIModelOperator


@dataclass
class RuntimeState:
    model: str
    installed: bool


class RoutingRuntime:

    def __init__(self, installed):
        self.installed = set(installed)

    def status(self):
        names = {
            "qwen_reasoning_9b",
            "qwen_reasoning_14b",
            "qwen_summary",
            "qwen_summary_14b",
            "qwen_coder",
        }

        return [
            RuntimeState(
                model=name,
                installed=name in self.installed,
            )
            for name in names
        ]


def test_reasoning_primary_is_qwen9():

    operator = AIModelOperator()

    runtime = RoutingRuntime([
        "qwen_reasoning_9b",
        "qwen_reasoning_14b",
    ])

    model = operator.select(
        "incident_reasoning",
        runtime,
    )

    assert model is not None
    assert model.name == "qwen_reasoning_9b"
    assert model.provider_model == "qwen3.5:9b"


def test_reasoning_14b_is_explicit_fallback():

    operator = AIModelOperator()

    primary = next(
        model
        for model in operator.list_models()
        if model.name == "qwen_reasoning_9b"
    )

    runtime = RoutingRuntime([
        "qwen_reasoning_14b",
    ])

    fallback = operator.fallback_candidates(
        primary,
        runtime,
    )

    assert [
        model.name
        for model in fallback
    ] == [
        "qwen_reasoning_14b"
    ]


def test_fallback_is_not_selected_as_primary():

    operator = AIModelOperator()

    runtime = RoutingRuntime([
        "qwen_reasoning_14b",
    ])

    selected = operator.select(
        "incident_reasoning",
        runtime,
    )

    assert selected is None


def test_explain_matches_primary_routing():

    operator = AIModelOperator()

    runtime = RoutingRuntime([
        "qwen_reasoning_9b",
        "qwen_reasoning_14b",
    ])

    selected = operator.select(
        "incident_reasoning",
        runtime,
    )

    explanation = operator.explain(
        "incident_reasoning",
        runtime,
    )

    assert explanation["available"] is True
    assert explanation["model"] == selected.name
    assert explanation["fallback"] is False


def test_explain_matches_fallback_routing():

    operator = AIModelOperator()

    runtime = RoutingRuntime([
        "qwen_reasoning_14b",
    ])

    explanation = operator.explain(
        "incident_reasoning",
        runtime,
    )

    assert explanation["available"] is True
    assert explanation["model"] == "qwen_reasoning_14b"
    assert explanation["fallback"] is True
    assert explanation["primary_model"] == "qwen_reasoning_9b"


def test_explain_reports_missing_models():

    operator = AIModelOperator()

    runtime = RoutingRuntime([
        "qwen_summary",
        "qwen_coder",
    ])

    explanation = operator.explain(
        "incident_reasoning",
        runtime,
    )

    assert explanation["available"] is False
    assert explanation["reason"] == "model_not_installed"
    assert explanation["model"] == "qwen_reasoning_9b"


def test_status_exposes_registered_models():

    operator = AIModelOperator()

    runtime = RoutingRuntime([
        "qwen_reasoning_9b",
        "qwen_reasoning_14b",
    ])

    status = operator.status(runtime)

    names = {
        item["name"]
        for item in status
    }

    assert "qwen_reasoning_9b" in names
    assert "qwen_reasoning_14b" in names
