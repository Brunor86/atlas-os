from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from atlas.services.ai.models import (
    AIReasoningStep,
    AIRecommendation,
    AIResponse,
)


def test_ai_recommendation_defaults_confidence():

    recommendation = AIRecommendation(
        title="Restart Jellyseerr",
        description="Restart the affected container.",
        priority="high",
    )

    assert recommendation.confidence == 1.0


def test_ai_recommendation_serializes():

    recommendation = AIRecommendation(
        title="Inspect DNS",
        description="Verify container DNS configuration.",
        priority="high",
        confidence=0.95,
    )

    assert recommendation.model_dump() == {
        "title": "Inspect DNS",
        "description": "Verify container DNS configuration.",
        "priority": "high",
        "confidence": 0.95,
    }


def test_ai_recommendation_rejects_invalid_confidence():

    with pytest.raises(ValidationError):
        AIRecommendation(
            title="Test",
            description="Test",
            priority="normal",
            confidence=-0.1,
        )

    with pytest.raises(ValidationError):
        AIRecommendation(
            title="Test",
            description="Test",
            priority="normal",
            confidence=1.1,
        )


def test_ai_reasoning_step_serializes():

    step = AIReasoningStep(
        step="Inspect DNS resolution",
        evidence="Jellyseerr cannot resolve external hosts.",
        impact="Application unavailable",
        confidence=0.98,
    )

    assert step.model_dump() == {
        "step": "Inspect DNS resolution",
        "evidence": "Jellyseerr cannot resolve external hosts.",
        "impact": "Application unavailable",
        "confidence": 0.98,
    }


def test_ai_reasoning_step_rejects_invalid_confidence():

    with pytest.raises(ValidationError):
        AIReasoningStep(
            step="Analyze",
            evidence="Evidence",
            impact="Impact",
            confidence=2.0,
        )


def test_ai_response_builds_nested_contracts():

    response = AIResponse(
        timestamp=datetime.now(timezone.utc),
        summary="Jellyseerr DNS failure detected.",
        overall_risk=80,
        overall_health=0.35,
        context={
            "asset": "jellyseerr",
        },
        incidents=[
            {
                "id": "INC-0001",
                "status": "active",
            }
        ],
        impacts=[
            {
                "asset": "jellyseerr",
                "severity": "high",
            }
        ],
        recommendations=[
            AIRecommendation(
                title="Inspect DNS",
                description="Inspect container DNS.",
                priority="high",
                confidence=0.95,
            )
        ],
        reasoning=[
            "DNS resolution failed."
        ],
        reasoning_steps=[
            AIReasoningStep(
                step="DNS analysis",
                evidence="Resolution failure observed.",
                impact="Jellyseerr unavailable.",
                confidence=0.98,
            )
        ],
    )

    assert response.overall_risk == 80
    assert response.overall_health == 0.35

    assert len(response.recommendations) == 1
    assert isinstance(
        response.recommendations[0],
        AIRecommendation,
    )

    assert len(response.reasoning_steps) == 1
    assert isinstance(
        response.reasoning_steps[0],
        AIReasoningStep,
    )


def test_ai_response_defaults_are_independent():

    first = AIResponse(
        timestamp=datetime.now(timezone.utc),
        summary="first",
        overall_risk=10,
        overall_health=0.9,
    )

    second = AIResponse(
        timestamp=datetime.now(timezone.utc),
        summary="second",
        overall_risk=20,
        overall_health=0.8,
    )

    first.context["x"] = 1
    first.incidents.append({"id": "INC-1"})
    first.reasoning.append("reason")

    assert second.context == {}
    assert second.incidents == []
    assert second.reasoning == []


def test_ai_response_rejects_unknown_fields():

    with pytest.raises(ValidationError):
        AIResponse(
            timestamp=datetime.now(timezone.utc),
            summary="test",
            overall_risk=10,
            overall_health=0.9,
            unexpected="value",
        )


def test_ai_response_assignment_is_validated():

    response = AIResponse(
        timestamp=datetime.now(timezone.utc),
        summary="test",
        overall_risk=10,
        overall_health=0.9,
    )

    with pytest.raises(ValidationError):
        response.overall_risk = "invalid"


def test_nested_dict_data_remains_supported():

    response = AIResponse(
        timestamp=datetime.now(timezone.utc),
        summary="test",
        overall_risk=10,
        overall_health=0.9,
        context={
            "nested": {
                "asset": "docker",
                "state": "degraded",
            }
        },
    )

    assert response.context["nested"]["asset"] == "docker"
