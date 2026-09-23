from atlas.services.intelligence.operator import (
    IntelligenceOperator,
)


class FakeContext:

    def __init__(
        self,
        incident,
    ):
        self.incidents = [
            incident
        ]

    def to_dict(
        self,
    ):
        return {
            "incidents":
                self.incidents,
        }


class FakeContextBuilder:

    def build_for_incident(
        self,
        incident_id,
    ):
        return FakeContext(
            {
                "id":
                    incident_id,

                "reason":
                    "synthetic healthy state",
            }
        )


class FakeSnapshotRepository:

    def get_history(
        self,
        limit=20,
    ):
        return []

    def get_latest(
        self,
    ):
        return None


class FakeAnalyzer:

    def analyze(
        self,
        metrics_history,
        snapshot=None,
    ):
        return []


class FakeReasoner:

    def reason(
        self,
        insights,
        context,
        dependency=None,
        asset_context=None,
    ):
        return {
            "state":
                "HEALTHY",

            "reasoning":
                [],

            "risks":
                [],

            "diagnoses":
                [],

            "recommended_actions":
                [],
        }


class FakeRecommendation:

    def recommend_from_reasoning(
        self,
        reasoning,
        incident_id=None,
        memory=None,
    ):
        return None


class FakeDecision:

    def build(
        self,
        reasoning=None,
        recommendation=None,
        memory=None,
    ):
        assert recommendation is None

        return {
            "state":
                "HEALTHY",

            "diagnoses":
                [],

            "diagnosis":
                {},
        }


class FakeExplanation:

    def explain(
        self,
        incident,
        reasoning=None,
        recommendation=None,
        learning=None,
    ):
        assert recommendation is None

        return {
            "explanation":
                [],
        }


def test_operator_accepts_no_recommendation_without_error():

    operator = IntelligenceOperator()

    operator.context_builder = (
        FakeContextBuilder()
    )

    operator.snapshot_repository = (
        FakeSnapshotRepository()
    )

    operator.analyzer = (
        FakeAnalyzer()
    )

    operator.reasoner = (
        FakeReasoner()
    )

    operator.recommendation = (
        FakeRecommendation()
    )

    operator.decision = (
        FakeDecision()
    )

    operator.explanation = (
        FakeExplanation()
    )

    result = operator.analyze(
        "INC-NO-ACTION"
    )

    assert result[
        "recommendation"
    ] is None

    assert result[
        "safety"
    ][
        "status"
    ] == "NO_ACTION"

    assert result[
        "result"
    ][
        "recommended_actions"
    ] == []
