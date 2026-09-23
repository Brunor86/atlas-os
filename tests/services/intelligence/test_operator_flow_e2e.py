from atlas.services.intelligence.operator import IntelligenceOperator


class FakeContext:

    def __init__(self, incident):
        self.incidents = [incident]
        self.knowledge = None

    def to_dict(self):
        return {
            "incidents": self.incidents,
        }


class FakeContextBuilder:

    def build_for_incident(self, incident_id):
        return FakeContext(
            {
                "id": incident_id,
                "asset_id": "asset-1",
                "reason": "DNS failure detected",
            }
        )


class FakeAnalyzer:

    def analyze(self, metrics_history, snapshot=None):
        return [
            {
                "type": "DNS_FAILURE",
                "category": "NETWORK",
                "severity": "HIGH",
                "asset": "jellyseerr",
            }
        ]


class FakeSnapshotRepository:

    def get_history(self, limit=20):
        return []

    def get_latest(self):
        return None


class FakeDependency:

    def impact(self, knowledge, asset_id):
        return {
            "asset_id": asset_id,
            "dependencies": [],
        }


class FakeMemory:

    def lookup(self, asset_id, issue):
        return None


class FakeRecommendation:

    def recommend_from_reasoning(
        self,
        reasoning,
        memory=None,
        incident_id=None,
    ):
        return {
            "action": "inspect logs",
            "incident_id": incident_id,
            "risk": "LOW",
            "confidence": 0.95,
            "reason": [
                "DNS failure detected",
            ],
            "evidence": [
                {
                    "type": "DNS_FAILURE",
                    "asset": "jellyseerr",
                }
            ],
        }


class FakeDecision:

    def build(
        self,
        reasoning=None,
        recommendation=None,
        memory=None,
    ):
        diagnosis = {
            "type": "DNS_FAILURE",
            "category": "NETWORK",
            "confidence": 0.95,
        }

        return {
            "state": "WARNING",
            "diagnoses": [
                diagnosis,
            ],
            "diagnosis": diagnosis,
        }


class FakeReasoner:

    def reason(
        self,
        insights,
        context,
        dependency=None,
        asset_context=None,
    ):
        return {
            "state": "WARNING",
            "reasoning": [
                "DNS resolution failure detected",
            ],
            "risks": [
                "Service availability may be affected",
            ],
            "diagnoses": [
                {
                    "type": "DNS_FAILURE",
                    "category": "NETWORK",
                    "confidence": 0.95,
                }
            ],
            "recommended_actions": [
                "inspect logs",
            ],
        }


class FakeExplanation:

    def explain(
        self,
        incident,
        reasoning=None,
        recommendation=None,
        learning=None,
    ):
        return {
            "explanation": [
                "DNS failure is associated with the affected service",
            ],
        }


class FakeToolResult:

    status = "SUCCESS"

    result = {
        "asset_id": "asset-1",
        "name": "jellyseerr",
        "type": "SERVICE",
    }


class FakeOperatorTools:

    def execute(self, *args, **kwargs):
        return FakeToolResult()


class FakeSafety:

    def evaluate(self, incident):
        return {
            "allowed": True,
            "safe": True,
            "requires_approval": False,
            "reason": "inspection is a read-only action",
        }


def test_operator_flow_e2e_preserves_diagnosis_recommendation_and_action():
    """
    E2E contract:

        operator
          -> context
          -> deterministic analysis
          -> dependency impact
          -> historical memory
          -> reasoning
          -> recommendation
          -> decision/diagnosis
          -> explanation
          -> safety
          -> unified result
    """

    operator = IntelligenceOperator()

    operator.context_builder = FakeContextBuilder()
    operator.analyzer = FakeAnalyzer()
    operator.snapshot_repository = FakeSnapshotRepository()
    operator.dependency = FakeDependency()
    operator.memory = FakeMemory()
    operator.recommendation = FakeRecommendation()
    operator.decision = FakeDecision()
    operator.reasoner = FakeReasoner()
    operator.explanation = FakeExplanation()
    operator.safety = FakeSafety()
    operator.tools = FakeOperatorTools()

    result = operator.analyze("INC-TEST")

    assert isinstance(result, dict)

    # Incident / context

    assert result["incident"]["id"] == "INC-TEST"
    assert result["incident"]["asset_id"] == "asset-1"
    assert result["context"]["incidents"]

    # Analysis

    assert result["insights"]
    assert result["insights"][0]["type"] == "DNS_FAILURE"

    # Reasoning

    assert result["reasoning"]["state"] == "WARNING"

    assert result["reasoning"]["diagnoses"][0]["type"] == (
        "DNS_FAILURE"
    )

    # Diagnosis

    assert result["decision"]["diagnosis"]["type"] == (
        "DNS_FAILURE"
    )

    assert result["decision"]["diagnosis"]["category"] == (
        "NETWORK"
    )

    # Recommendation

    recommendation = result["recommendation"]

    assert recommendation["action"] == "inspect logs"
    assert recommendation["incident_id"] == "INC-TEST"
    assert recommendation["confidence"] == 0.95
    assert recommendation["risk"] == "LOW"

    # Explanation

    assert result["explanation"]["explanation"]

    # Safety

    assert result["safety"]["allowed"] is True
    assert result["safety"]["safe"] is True

    # Unified operator-facing result

    unified = result["result"]

    assert unified["state"] == "WARNING"

    assert unified["diagnosis"]["type"] == (
        "DNS_FAILURE"
    )

    assert unified["diagnoses"][0]["type"] == (
        "DNS_FAILURE"
    )

    assert unified["recommended_actions"]

    action = unified["recommended_actions"][0]

    assert action["action"] == "inspect logs"
    assert action["incident_id"] == "INC-TEST"
    assert action["confidence"] == 0.95
    assert action["risk"] == "LOW"

    assert action["safety"]["allowed"] is True
    assert action["safety"]["safe"] is True
