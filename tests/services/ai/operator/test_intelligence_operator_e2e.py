from dataclasses import dataclass

from atlas.services.ai.operator.operator import (
    AIModelOperator,
)
from atlas.services.ai.operator.tools.intelligence import (
    IntelligenceToolAdapter,
    IntelligenceToolBridge,
)


@dataclass
class FakeRegistryResult:

    status: str = "SUCCESS"

    result: dict | None = None

    error: str | None = None

    evidence: list | None = None


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

        return FakeRegistryResult(
            status="SUCCESS",
            result={
                "incident": {
                    "id": kwargs["incident_id"],
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
                    "incident_id": kwargs["incident_id"],
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
                            "incident_id": kwargs["incident_id"],
                            "confidence": 0.95,
                            "risk": "LOW",
                            "safety": {
                                "allowed": True,
                                "safe": True,
                            },
                        }
                    ],
                },
            },
            evidence=[
                {
                    "type": "DNS_FAILURE",
                    "asset": "jellyseerr",
                }
            ],
        )


def test_intelligence_tool_adapter_preserves_operational_result():

    registry = FakeIntelligenceRegistry()

    adapter = IntelligenceToolAdapter(
        registry=registry,
        name="analyze_incident",
        description="Analyze an incident.",
    )

    result = adapter.execute(
        incident_id="INC-E2E",
    )

    assert result.tool == "analyze_incident"
    assert result.success is True
    assert result.error is None

    assert result.data["incident"]["id"] == "INC-E2E"

    assert (
        result.data["decision"]["diagnosis"]["type"]
        == "DNS_FAILURE"
    )

    assert (
        result.data["recommendation"]["action"]
        == "inspect logs"
    )

    assert (
        result.data["safety"]["allowed"]
        is True
    )

    assert result.evidence == [
        {
            "type": "DNS_FAILURE",
            "asset": "jellyseerr",
        }
    ]

    assert registry.calls == [
        {
            "name": "analyze_incident",
            "kwargs": {
                "incident_id": "INC-E2E",
            },
        }
    ]


def test_intelligence_tool_bridge_exposes_registry_tools():

    registry = FakeIntelligenceRegistry()

    bridge = IntelligenceToolBridge(
        registry
    )

    tools = bridge.tools()

    assert len(tools) == 1

    tool = tools[0]

    assert isinstance(
        tool,
        IntelligenceToolAdapter,
    )

    assert tool.name == "analyze_incident"

    result = tool.execute(
        incident_id="INC-BRIDGE",
    )

    assert result.success is True
    assert result.data["incident"]["id"] == "INC-BRIDGE"


def test_ai_model_operator_exposes_intelligence_tools():

    registry = FakeIntelligenceRegistry()

    operator = AIModelOperator(
        tool_registry=registry
    )

    tools = operator.list_tools()

    assert len(tools) == 1

    tool = operator.get_tool(
        "analyze_incident"
    )

    assert tool is not None
    assert tool.name == "analyze_incident"


def test_ai_model_operator_executes_intelligence_e2e():

    registry = FakeIntelligenceRegistry()

    operator = AIModelOperator(
        tool_registry=registry
    )

    result = operator.execute_tool(
        "analyze_incident",
        incident_id="INC-OPERATOR",
    )

    assert result.tool == "analyze_incident"
    assert result.success is True

    data = result.data

    assert data["incident"]["id"] == "INC-OPERATOR"

    assert (
        data["decision"]["diagnosis"]["type"]
        == "DNS_FAILURE"
    )

    assert (
        data["recommendation"]["action"]
        == "inspect logs"
    )

    assert (
        data["recommendation"]["incident_id"]
        == "INC-OPERATOR"
    )

    assert data["recommendation"]["risk"] == "LOW"
    assert data["recommendation"]["confidence"] == 0.95

    assert data["safety"]["allowed"] is True
    assert data["safety"]["safe"] is True

    unified = data["result"]

    assert unified["state"] == "WARNING"

    assert (
        unified["diagnosis"]["type"]
        == "DNS_FAILURE"
    )

    action = unified["recommended_actions"][0]

    assert action["action"] == "inspect logs"
    assert action["incident_id"] == "INC-OPERATOR"
    assert action["confidence"] == 0.95
    assert action["risk"] == "LOW"
    assert action["safety"]["allowed"] is True
    assert action["safety"]["safe"] is True

    assert result.evidence == [
        {
            "type": "DNS_FAILURE",
            "asset": "jellyseerr",
        }
    ]
