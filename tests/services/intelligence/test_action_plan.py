from atlas.models.action_plan import ActionPlan


def test_action_plan_preserves_operational_contract():

    plan = ActionPlan(
        action="restart container",
        target="jellyseerr",
        incident_id="INC-TEST",
        reason=[
            "DNS failure detected",
        ],
        evidence=[
            {
                "source": "docker",
                "type": "dns",
                "value": "resolution failed",
            }
        ],
        risk="LOW",
        prerequisites=[
            "verify container is running",
        ],
        rollback="docker start jellyseerr",
        confidence=0.95,
    )

    result = plan.to_dict()

    assert result["action"] == "restart container"
    assert result["target"] == "jellyseerr"
    assert result["incident_id"] == "INC-TEST"

    assert result["reason"] == [
        "DNS failure detected",
    ]

    assert result["evidence"][0]["type"] == "dns"

    assert result["risk"] == "LOW"

    assert result["prerequisites"] == [
        "verify container is running",
    ]

    assert (
        result["rollback"]
        == "docker start jellyseerr"
    )

    assert result["confidence"] == 0.95

from atlas.services.intelligence.action.builder import SafeActionBuilder


def test_safe_action_builder_preserves_action_plan_fields():

    plan = ActionPlan(
        action="restart container",
        target="jellyseerr",
        incident_id="INC-TEST",
        reason=[
            "DNS failure detected",
        ],
        evidence=[
            {
                "source": "docker",
                "type": "dns",
                "value": "resolution failed",
            }
        ],
        risk="LOW",
        prerequisites=[
            "verify container is running",
        ],
        rollback="docker start jellyseerr",
        confidence=0.95,
    )

    result = SafeActionBuilder().build(
        plan.to_dict()
    )

    assert result.action == "restart container"
    assert result.target == "jellyseerr"
    assert result.incident_id == "INC-TEST"
    assert result.risk == "LOW"
    assert result.rollback == "docker start jellyseerr"
    assert result.status == "PENDING_APPROVAL"
    assert result.requires_approval is True
    assert result.evidence[0]["type"] == "dns"


def test_safe_action_builder_returns_none_without_action():

    result = SafeActionBuilder().build(
        {
            "incident_id": "INC-TEST",
            "risk": "LOW",
        }
    )

    assert result is None

from atlas.services.intelligence.recommendation.service import (
    ActionRecommendationService,
)


def test_recommendation_builds_action_plan():

    service = ActionRecommendationService()

    reasoning = {
        "recommended_actions": [
            {
                "action": "restart container",
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
        ]
    }

    result = service.recommend_from_reasoning(
        reasoning,
        incident_id="INC-TEST",
    )

    assert isinstance(
        result,
        ActionPlan,
    )

    assert result.action == "restart container"
    assert result.target == "jellyseerr"
    assert result.incident_id == "INC-TEST"
    assert result.risk == "LOW"
    assert result.confidence == 0.95
    assert result.reason == [
        "DNS failure detected",
    ]
    assert result.evidence[0]["type"] == "dns"


def test_recommendation_without_action_returns_none():

    service = ActionRecommendationService()

    result = service.recommend_from_reasoning(
        {
            "recommended_actions": [],
        },
        incident_id="INC-TEST",
    )

    assert result is None



def test_decision_service_accepts_action_plan():

    from atlas.services.intelligence.decision.service import (
        IntelligenceDecisionService,
    )

    plan = ActionPlan(
        action="restart container",
        target="jellyseerr",
        incident_id="INC-TEST",
        reason=[
            "DNS failure detected",
        ],
        evidence=[
            {
                "source": "docker",
                "type": "dns",
                "value": "resolution failed",
            }
        ],
        risk="LOW",
        confidence=0.95,
    )

    result = IntelligenceDecisionService().build(
        reasoning={},
        recommendation=plan,
    )

    assert result["action"] == "restart container"
    assert result["confidence"] == 0.95
    assert result["risk"] == "LOW"
    assert result["source"] == "recommendation"
    assert result["reasons"] == [
        "DNS failure detected",
    ]
    assert result["evidence"][0]["type"] == "dns"
