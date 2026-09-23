from atlas.services.ai.service import AIService
from atlas.services.ai.models import LLMResponse
from atlas.models.noc import NOCIncident


def test_ai_incident_reasoning_applies_structured_result():
    service = AIService()

    incident = NOCIncident(
        name="nginx-proxy-manager",
        confidence=0.7,
        reason="Container stopped",
        asset="nginx-proxy-manager",
        severity="CRITICAL",
        incident_score=90,
        root_cause="container unavailable",
        diagnosis="Reverse proxy container is stopped",
        evidence=[
            "container stopped",
        ],
        impact=[
            "reverse proxy unavailable",
        ],
    )

    def fake_ask(request):
        assert request.task == "incident_reasoning"
        assert request.user_prompt

        return LLMResponse(
            model="qwen_reasoning",
            provider="ollama",
            content=(
                '{"summary": "Reverse proxy unavailable",'
                '"root_cause": "container stopped",'
                '"evidence": ["container stopped"],'
                '"impact": ["reverse proxy unavailable"],'
                '"risk": "CRITICAL",'
                '"recommendation": "Restart container",'
                '"missing_evidence": [],'
                '"confidence": 0.9}'
            ),
            latency_ms=12.5,
        )

    service.ask = fake_ask

    result = service.analyze_incident_reasoning(
        incident
    )

    assert result["summary"] == (
        "Reverse proxy unavailable"
    )

    assert result["root_cause"] == (
        "container stopped"
    )

    assert result["risk"] == "CRITICAL"

    assert result["recommendation"] == (
        "Restart container"
    )

    assert result["confidence"] == 0.9

    assert incident.ai_analysis["risk"] == (
        "CRITICAL"
    )

    assert incident.ai_recommendation == (
        "Restart container"
    )

    assert incident.ai_confidence == 0.9

    assert incident.ai_reasoning == [
        {
            "type": "root_cause",
            "content": "container stopped",
        },
        {
            "type": "evidence",
            "content": "container stopped",
        },
        {
            "type": "impact",
            "content": "reverse proxy unavailable",
        },
    ]

    assert (
        incident.ai_analysis["_metadata"]["model"]
        == "qwen_reasoning"
    )

    assert (
        incident.ai_analysis["_metadata"]["provider"]
        == "ollama"
    )
