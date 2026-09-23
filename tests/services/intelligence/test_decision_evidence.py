from atlas.services.intelligence.decision.service import (
    IntelligenceDecisionService,
)


def test_decision_preserves_recommendation_evidence():

    service = IntelligenceDecisionService()

    recommendation = {
        "action": "inspect logs",
        "incident_id": "INC-0001",
        "status": "reasoning_recommended",
        "confidence": 0.9,
        "risk": "LOW",
        "reason": [
            "Investigate dns observation for asset jellyseerr",
        ],
        "evidence": [
            {
                "source": "reasoning",
                "observation": {
                    "type": "dns",
                    "value": "resolution failed",
                    "severity": "WARNING",
                    "source": "docker",
                },
            },
        ],
    }

    decision = service.build(
        reasoning={
            "recommended_actions": [],
        },
        recommendation=recommendation,
    )

    assert decision["action"] == "inspect logs"

    assert decision["confidence"] == 0.9

    assert decision["risk"] == "LOW"

    assert decision["source"] == "recommendation"

    assert len(decision["evidence"]) == 1

    evidence = decision["evidence"][0]

    assert evidence["source"] == "reasoning"

    assert evidence["observation"]["type"] == "dns"

    assert (
        evidence["observation"]["value"]
        == "resolution failed"
    )

    assert (
        evidence["observation"]["severity"]
        == "WARNING"
    )

    assert (
        evidence["observation"]["source"]
        == "docker"
    )
