from atlas.services.intelligence.recommendation.service import (
    ActionRecommendationService,
)


def test_reasoning_recommendation_preserves_action_evidence():

    service = ActionRecommendationService()

    reasoning = {
        "recommended_actions": [
            {
                "action": "inspect logs",
                "reason": (
                    "Investigate dns observation "
                    "for asset jellyseerr"
                ),
                "risk": "LOW",
                "asset_id": "asset-1",
                "evidence": {
                    "type": "dns",
                    "value": "resolution failed",
                    "severity": "WARNING",
                    "source": "docker",
                },
            },
        ],
    }

    result = service.recommend_from_reasoning(
        reasoning=reasoning,
    )

    assert result["action"] == "inspect logs"

    assert result["risk"] == "LOW"

    assert result["status"] == "reasoning_recommended"

    assert len(result["evidence"]) == 1

    evidence = result["evidence"][0]

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
