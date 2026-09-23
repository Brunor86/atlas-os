from types import SimpleNamespace

from atlas.services.ai.operator.operator import AIModelOperator


class FakeRuntime:

    def __init__(self, states):
        self._states = states

    def status(self):
        return self._states


def runtime_state(model, installed=True):
    return SimpleNamespace(
        model=model,
        installed=installed,
    )


def test_operator_status_exposes_all_registered_models():

    operator = AIModelOperator()

    runtime = FakeRuntime([
        runtime_state("qwen_reasoning_9b", True),
        runtime_state("qwen_summary", True),
        runtime_state("qwen_coder", True),
        runtime_state("qwen_reasoning_14b", True),
        runtime_state("qwen_summary_14b", True),
    ])

    status = operator.status(runtime)

    assert isinstance(status, list)

    assert len(status) == len(operator.models)

    models = {
        item["model"]
        for item in status
    }

    assert "qwen_reasoning_9b" in models
    assert "qwen_summary" in models
    assert "qwen_coder" in models


def test_operator_explain_reports_capability_and_model():

    operator = AIModelOperator()

    runtime = FakeRuntime([
        runtime_state("qwen_reasoning_9b", True),
        runtime_state("qwen_summary", True),
        runtime_state("qwen_coder", True),
        runtime_state("qwen_reasoning_14b", True),
        runtime_state("qwen_summary_14b", True),
    ])

    explanation = operator.explain(
        "incident_reasoning",
        runtime,
    )

    assert isinstance(
        explanation,
        dict,
    )

    assert explanation["available"] is True

    assert explanation["model"] == "qwen_reasoning_9b"

    assert explanation["provider_model"] == "qwen3.5:9b"

    assert explanation["task"] == "incident_reasoning"

    assert explanation["capability"] == "reasoning"


def test_operator_explain_reports_missing_primary_model():

    operator = AIModelOperator()

    runtime = FakeRuntime([
        runtime_state(
            "qwen_reasoning_9b",
            False,
        ),
        runtime_state(
            "qwen_reasoning_14b",
            True,
        ),
    ])

    explanation = operator.explain(
        "incident_reasoning",
        runtime,
    )

    assert explanation["available"] is True

    assert explanation["model"] == "qwen_reasoning_14b"

    assert explanation["provider_model"] == "qwen2.5:14b"


def test_operator_explain_reports_missing_capable_models():

    operator = AIModelOperator()

    runtime = FakeRuntime([
        runtime_state(
            "qwen_summary",
            True,
        ),
        runtime_state(
            "qwen_coder",
            True,
        ),
    ])

    explanation = operator.explain(
        "incident_reasoning",
        runtime,
    )

    assert explanation["available"] is False

    assert explanation["reason"] == "model_not_installed"

    assert explanation["task"] == "incident_reasoning"

    assert explanation["capability"] == "reasoning"
