from atlas.services.intelligence.operator import IntelligenceOperator


def test_operator_safety_incident_preserves_diagnosis():

    incident = {
        "id": "INC-TEST",
        "asset_id": "asset-1",
        "reason": "DNS failure detected",
    }

    recommendation = {
        "action": "inspect logs",
        "incident_id": "INC-TEST",
        "risk": "LOW",
        "confidence": 0.95,
    }

    diagnosis = {
        "type": "DNS_FAILURE",
        "category": "NETWORK",
        "confidence": 0.95,
    }

    safety_incident = (
        IntelligenceOperator._build_safety_incident(
            incident,
            recommendation,
            diagnosis=diagnosis,
        )
    )

    assert safety_incident.diagnosis == diagnosis


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
                "reason": "SMART failure detected",
            }
        )


class FakeAnalyzer:

    def analyze(self, metrics_history, snapshot=None):
        return []


class FakeDependency:

    def impact(self, knowledge, asset_id):
        return {}


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
            "action": "restart",
            "incident_id": incident_id,
            "risk": "HIGH",
            "confidence": 0.98,
            "reason": [
                "storage health failure"
            ],
            "evidence": [],
        }


class FakeDecision:

    def build(
        self,
        reasoning=None,
        recommendation=None,
        memory=None,
    ):
        return {
            "state": "CRITICAL",
            "diagnoses": [
                {
                    "type": "STORAGE_HEALTH_FAILURE",
                    "category": "STORAGE",
                    "confidence": 0.98,
                }
            ],
            "diagnosis": {
                "type": "STORAGE_HEALTH_FAILURE",
                "category": "STORAGE",
                "confidence": 0.98,
            },
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
            "state": "CRITICAL",
            "reasoning": [],
            "risks": [],
            "diagnoses": [
                {
                    "type": "STORAGE_HEALTH_FAILURE",
                    "category": "STORAGE",
                    "confidence": 0.98,
                }
            ],
            "recommended_actions": [],
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
            "explanation": [],
        }


class FakeSnapshotRepository:

    def get_history(self, limit=20):
        return []

    def get_latest(self):
        return None


class FakeToolResult:

    status = "SUCCESS"
    result = {}


class FakeOperatorTools:

    def execute(self, *args, **kwargs):
        return FakeToolResult()



def test_operator_real_intelligence_pipeline_preserves_action_plan():

    operator = IntelligenceOperator()

    class IntegrationContext:

        incidents = [
            {
                "id": "INC-TEST",
                "asset_id": "asset-1",
                "reason": "DNS failure detected",
            }
        ]

        knowledge = None

        def to_dict(self):
            return {
                "incidents": self.incidents,
            }

    class IntegrationContextBuilder:

        def build_for_incident(self, incident_id):
            return IntegrationContext()

    class IntegrationSnapshotRepository:

        def get_history(self, limit=20):
            return []

        def get_latest(self):
            return None

    class IntegrationAnalyzer:

        def analyze(self, metrics_history, snapshot=None):
            return []

    class IntegrationReasoner:

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
                    "DNS failure detected for jellyseerr",
                ],
                "risks": [],
                "diagnoses": [
                    {
                        "type": "DNS_FAILURE",
                        "category": "NETWORK",
                        "confidence": 0.95,
                        "evidence": {
                            "observation_type": "dns",
                            "asset": "jellyseerr",
                            "value": "resolution failed",
                        },
                    }
                ],
                "recommended_actions": [
                    {
                        "action": "inspect logs",
                        "target": "jellyseerr",
                        "risk": "LOW",
                        "confidence": 0.95,
                        "reason": "DNS failure detected",
                        "evidence": {
                            "source": "docker",
                            "type": "dns",
                            "value": "resolution failed",
                        },
                    }
                ],
            }

    class IntegrationDependency:

        def impact(self, knowledge, asset_id):
            return {}

    class IntegrationMemory:

        def lookup(self, asset_id, issue):
            return None

    class IntegrationToolResult:

        status = "SUCCESS"
        result = {}

    operator.context_builder = (
        IntegrationContextBuilder()
    )

    operator.snapshot_repository = (
        IntegrationSnapshotRepository()
    )

    operator.analyzer = IntegrationAnalyzer()

    operator.reasoner = IntegrationReasoner()

    operator.dependency = IntegrationDependency()

    operator.memory = IntegrationMemory()

    operator.execute_tool = (
        lambda *args, **kwargs:
        IntegrationToolResult()
    )

    result = operator.analyze(
        "INC-TEST"
    )

    recommendation = result["recommendation"]

    assert recommendation is not None

    assert recommendation.action == (
        "inspect logs"
    )

    assert recommendation.target == (
        "jellyseerr"
    )

    assert recommendation.incident_id == (
        "INC-TEST"
    )

    assert recommendation.risk == "LOW"

    assert recommendation.confidence == 0.95

    assert recommendation.reason == [
        "DNS failure detected"
    ]

    assert recommendation.evidence[0]["type"] == (
        "dns"
    )

    decision = result["decision"]

    assert decision["action"] == (
        "inspect logs"
    )

    assert decision["source"] == (
        "recommendation"
    )

    assert decision["risk"] == "LOW"

    assert decision["confidence"] == 0.95

    assert decision["evidence"][0]["type"] == (
        "dns"
    )

    explanation = result["explanation"]

    assert any(
        "inspect logs" in item
        for item in explanation["explanation"]
    )

    safety = result["safety"]

    assert safety is not None

    assert (
        result["result"]["recommended_actions"][0][
            "action"
        ]
        == "inspect logs"
    )

    assert (
        result["result"]["recommended_actions"][0][
            "confidence"
        ]
        == 0.95
    )

    assert (
        result["result"]["recommended_actions"][0][
            "risk"
        ]
        == "LOW"
    )

def test_operator_propagates_diagnosis_to_safety():

    operator = IntelligenceOperator()

    operator.context_builder = FakeContextBuilder()
    operator.snapshot_repository = FakeSnapshotRepository()
    operator.analyzer = FakeAnalyzer()
    operator.reasoner = FakeReasoner()
    operator.dependency = FakeDependency()
    operator.memory = FakeMemory()
    operator.recommendation = FakeRecommendation()
    operator.decision = FakeDecision()
    operator.explanation = FakeExplanation()

    operator.execute_tool = (
        lambda *args, **kwargs: FakeToolResult()
    )

    result = operator.analyze(
        "INC-TEST"
    )

    safety = (
        result["result"]["recommended_actions"][0]["safety"]
    )

    assert safety["status"] == "BLOCKED"
