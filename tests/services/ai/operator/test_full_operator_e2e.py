from types import SimpleNamespace

from atlas.services.ai.operator.operator import AIModelOperator


class FakeRegistryResult:

    def __init__(self, data):
        self.status = "SUCCESS"
        self.result = data
        self.error = None
        self.evidence = [
            {
                "type": "DNS_FAILURE",
                "asset": "jellyseerr",
            }
        ]


class FakeRuntime:

    def status(self):
        return [
            SimpleNamespace(
                model="qwen_reasoning_9b",
                installed=True,
            ),
            SimpleNamespace(
                model="qwen_summary",
                installed=True,
            ),
            SimpleNamespace(
                model="qwen_coder",
                installed=True,
            ),
            SimpleNamespace(
                model="qwen_reasoning_14b",
                installed=True,
            ),
            SimpleNamespace(
                model="qwen_summary_14b",
                installed=True,
            ),
        ]


class FakeIntelligenceRegistry:

    def __init__(self):
        self.calls = []

    def describe(self):
        return [
            {
                "name": "analyze_incident",
                "description": (
                    "Analyze an incident through the "
                    "ATLAS intelligence pipeline."
                ),
            }
        ]

    def execute(self, name, **kwargs):

        self.calls.append(
            {
                "name": name,
                "kwargs": kwargs,
            }
        )

        incident_id = kwargs["incident_id"]

        return FakeRegistryResult(
            {
                "incident": {
                    "id": incident_id,
                },
                "decision": {
                    "state": "WARNING",
                    "diagnosis": {
                        "type": "DNS_FAILURE",
                        "category": "NETWORK",
                        "confidence": 0.95,
                    },
                },
                "recommendation": {
                    "action": "inspect logs",
                    "incident_id": incident_id,
                    "risk": "LOW",
                    "confidence": 0.95,
                },
                "safety": {
                    "allowed": True,
                    "safe": True,
                },
                "result": {
                    "state": "WARNING",
                    "diagnosis": {
                        "type": "DNS_FAILURE",
                        "category": "NETWORK",
                        "confidence": 0.95,
                    },
                    "recommended_actions": [
                        {
                            "action": "inspect logs",
                            "incident_id": incident_id,
                            "confidence": 0.95,
                            "risk": "LOW",
                            "safety": {
                                "allowed": True,
                                "safe": True,
                            },
                        }
                    ],
                },
            }
        )


def test_full_ai_operator_e2e():

    registry = FakeIntelligenceRegistry()

    operator = AIModelOperator(
        tool_registry=registry
    )

    # -------------------------------------------------
    # 1. Operator understands the task
    # -------------------------------------------------

    assert (
        operator.capability_for_task(
            "incident_reasoning"
        )
        == "reasoning"
    )

    # -------------------------------------------------
    # 2. Operator selects the primary reasoning model
    # -------------------------------------------------

    runtime = FakeRuntime()

    model = operator.select(
        "incident_reasoning",
        runtime=runtime,
    )

    assert model.name == "qwen_reasoning_9b"
    assert model.provider == "ollama"
    assert model.provider_model == "qwen3.5:9b"

    # Heavy fallback must not win during normal selection.
    assert model.fallback_for is None

    # -------------------------------------------------
    # 3. Operator exposes the real intelligence tool
    # -------------------------------------------------

    tool = operator.get_tool(
        "analyze_incident"
    )

    assert tool is not None
    assert tool.name == "analyze_incident"

    # -------------------------------------------------
    # 4. Operator executes the intelligence pipeline
    # -------------------------------------------------

    result = operator.execute_tool(
        "analyze_incident",
        incident_id="INC-FULL-E2E",
    )

    assert result.success is True
    assert result.error is None

    # -------------------------------------------------
    # 5. Tool reached the intelligence registry
    # -------------------------------------------------

    assert registry.calls == [
        {
            "name": "analyze_incident",
            "kwargs": {
                "incident_id": "INC-FULL-E2E",
            },
        }
    ]

    data = result.data

    # -------------------------------------------------
    # 6. Diagnosis survived the complete chain
    # -------------------------------------------------

    assert (
        data["decision"]["diagnosis"]["type"]
        == "DNS_FAILURE"
    )

    assert (
        data["decision"]["diagnosis"]["category"]
        == "NETWORK"
    )

    assert (
        data["decision"]["diagnosis"]["confidence"]
        == 0.95
    )

    # -------------------------------------------------
    # 7. Recommendation survived
    # -------------------------------------------------

    recommendation = data["recommendation"]

    assert recommendation["action"] == "inspect logs"
    assert recommendation["incident_id"] == "INC-FULL-E2E"
    assert recommendation["risk"] == "LOW"
    assert recommendation["confidence"] == 0.95

    # -------------------------------------------------
    # 8. Safety gate survived
    # -------------------------------------------------

    assert data["safety"]["allowed"] is True
    assert data["safety"]["safe"] is True

    # -------------------------------------------------
    # 9. Unified operational result survived
    # -------------------------------------------------

    unified = data["result"]

    assert unified["state"] == "WARNING"

    assert (
        unified["diagnosis"]["type"]
        == "DNS_FAILURE"
    )

    assert len(
        unified["recommended_actions"]
    ) == 1

    action = unified["recommended_actions"][0]

    assert action["action"] == "inspect logs"
    assert action["incident_id"] == "INC-FULL-E2E"
    assert action["confidence"] == 0.95
    assert action["risk"] == "LOW"

    assert action["safety"]["allowed"] is True
    assert action["safety"]["safe"] is True

    # -------------------------------------------------
    # 10. Evidence survived the operator boundary
    # -------------------------------------------------

    assert result.evidence == [
        {
            "type": "DNS_FAILURE",
            "asset": "jellyseerr",
        }
    ]



class FallbackRuntime:

    def __init__(self, installed_models):
        self.installed_models = set(installed_models)

    def status(self):
        return [
            SimpleNamespace(
                model="qwen_reasoning_9b",
                installed="qwen_reasoning_9b" in self.installed_models,
            ),
            SimpleNamespace(
                model="qwen_reasoning_14b",
                installed="qwen_reasoning_14b" in self.installed_models,
            ),
            SimpleNamespace(
                model="qwen_summary",
                installed="qwen_summary" in self.installed_models,
            ),
            SimpleNamespace(
                model="qwen_summary_14b",
                installed="qwen_summary_14b" in self.installed_models,
            ),
            SimpleNamespace(
                model="qwen_coder",
                installed="qwen_coder" in self.installed_models,
            ),
        ]


def test_ai_operator_selects_primary_reasoning_model_when_available():

    registry = FakeIntelligenceRegistry()

    operator = AIModelOperator(
        tool_registry=registry
    )

    runtime = FallbackRuntime(
        [
            "qwen_reasoning_9b",
            "qwen_reasoning_14b",
        ]
    )

    model = operator.select(
        "incident_reasoning",
        runtime=runtime,
    )

    assert model is not None
    assert model.name == "qwen_reasoning_9b"
    assert model.provider_model == "qwen3.5:9b"

    fallback = operator.fallback_candidates(
        model,
        runtime,
    )

    assert len(fallback) == 1
    assert fallback[0].name == "qwen_reasoning_14b"


def test_ai_operator_uses_14b_fallback_when_primary_is_unavailable():

    registry = FakeIntelligenceRegistry()

    operator = AIModelOperator(
        tool_registry=registry
    )

    runtime = FallbackRuntime(
        [
            "qwen_reasoning_14b",
        ]
    )

    primary = operator.select(
        "incident_reasoning",
        runtime=runtime,
    )

    assert primary is None

    primary_profile = next(
        model
        for model in operator.list_models()
        if model.name == "qwen_reasoning_9b"
    )

    fallback = operator.fallback_candidates(
        primary_profile,
        runtime,
    )

    assert len(fallback) == 1

    selected = fallback[0]

    assert selected.name == "qwen_reasoning_14b"
    assert selected.provider_model == "qwen2.5:14b"
    assert selected.fallback_for == "qwen_reasoning_9b"


def test_ai_operator_does_not_use_heavy_fallback_when_primary_is_available():

    registry = FakeIntelligenceRegistry()

    operator = AIModelOperator(
        tool_registry=registry
    )

    runtime = FallbackRuntime(
        [
            "qwen_reasoning_9b",
            "qwen_reasoning_14b",
        ]
    )

    selected = operator.select(
        "incident_reasoning",
        runtime=runtime,
    )

    assert selected.name == "qwen_reasoning_9b"

    assert selected.name != "qwen_reasoning_14b"

    fallback = operator.fallback_candidates(
        selected,
        runtime,
    )

    assert [
        model.name
        for model in fallback
    ] == [
        "qwen_reasoning_14b"
    ]



def test_ai_operator_fallback_completes_operational_flow():

    registry = FakeIntelligenceRegistry()

    operator = AIModelOperator(
        tool_registry=registry
    )

    # -------------------------------------------------
    # 1. Primary reasoning model unavailable
    # -------------------------------------------------

    runtime = FallbackRuntime(
        [
            "qwen_reasoning_14b",
        ]
    )

    primary = next(
        model
        for model in operator.list_models()
        if model.name == "qwen_reasoning_9b"
    )

    assert operator.can_use(
        "qwen_reasoning_9b",
        runtime,
    ) is False

    # -------------------------------------------------
    # 2. Fallback model is available
    # -------------------------------------------------

    fallback = operator.fallback_candidates(
        primary,
        runtime,
    )

    assert len(fallback) == 1

    selected = fallback[0]

    assert selected.name == "qwen_reasoning_14b"
    assert selected.provider == "ollama"
    assert selected.provider_model == "qwen2.5:14b"

    # -------------------------------------------------
    # 3. Operator executes the intelligence tool
    # -------------------------------------------------

    result = operator.execute_tool(
        "analyze_incident",
        incident_id="INC-FALLBACK-E2E",
    )

    assert result.tool == "analyze_incident"
    assert result.success is True
    assert result.error is None

    # -------------------------------------------------
    # 4. Operational chain survives fallback
    # -------------------------------------------------

    data = result.data

    assert data["incident"]["id"] == "INC-FALLBACK-E2E"

    assert (
        data["decision"]["diagnosis"]["type"]
        == "DNS_FAILURE"
    )

    assert (
        data["decision"]["diagnosis"]["category"]
        == "NETWORK"
    )

    assert (
        data["recommendation"]["action"]
        == "inspect logs"
    )

    assert (
        data["recommendation"]["incident_id"]
        == "INC-FALLBACK-E2E"
    )

    assert data["recommendation"]["risk"] == "LOW"
    assert data["recommendation"]["confidence"] == 0.95

    # -------------------------------------------------
    # 5. Safety remains authoritative
    # -------------------------------------------------

    assert data["safety"]["allowed"] is True
    assert data["safety"]["safe"] is True

    # -------------------------------------------------
    # 6. Unified operator result remains intact
    # -------------------------------------------------

    unified = data["result"]

    assert unified["state"] == "WARNING"

    assert (
        unified["diagnosis"]["type"]
        == "DNS_FAILURE"
    )

    assert (
        unified["diagnosis"]["category"]
        == "NETWORK"
    )

    assert len(
        unified["recommended_actions"]
    ) == 1

    action = unified["recommended_actions"][0]

    assert action["action"] == "inspect logs"
    assert action["incident_id"] == "INC-FALLBACK-E2E"
    assert action["confidence"] == 0.95
    assert action["risk"] == "LOW"

    assert action["safety"]["allowed"] is True
    assert action["safety"]["safe"] is True

    # -------------------------------------------------
    # 7. Intelligence registry received the operation
    # -------------------------------------------------

    assert registry.calls == [
        {
            "name": "analyze_incident",
            "kwargs": {
                "incident_id": "INC-FALLBACK-E2E",
            },
        }
    ]
