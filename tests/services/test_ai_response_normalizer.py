import json

from atlas.services.ai.service import AIService


def normalize(value):
    return AIService._parse_reasoning_response(value)


def test_plain_json():
    raw = json.dumps({
        "summary": "Docker DNS failure",
        "root_cause": "Docker DNS resolution failure",
        "evidence": ["getaddrinfo EAI_AGAIN"],
        "impact": ["container cannot resolve external names"],
        "risk": "LOW",
        "recommendation": "inspect Docker DNS configuration",
        "missing_evidence": ["Docker network configuration"],
        "confidence": 0.91,
    })

    result = normalize(raw)

    assert result["parse_error"] is False
    assert result["root_cause"] == "Docker DNS resolution failure"
    assert result["evidence"] == ["getaddrinfo EAI_AGAIN"]
    assert result["risk"] == "LOW"
    assert result["confidence"] == 0.91


def test_qwen_analysis_wrapper():
    raw = json.dumps({
        "analysis": {
            "likely_root_cause": "Network configuration issue or DNS resolution problem",
            "evidence_supporting_it": [
                "Docker reports getaddrinfo EAI_AGAIN",
                "Container cannot resolve external names",
            ],
            "missing_evidence": [
                "Docker network configuration",
            ],
            "safest_next_diagnostic_action": (
                "Run a network connectivity test within the container"
            ),
        }
    })

    result = normalize(raw)

    assert result["parse_error"] is False
    assert "DNS" in result["root_cause"]
    assert len(result["evidence"]) == 2
    assert result["missing_evidence"] == [
        "Docker network configuration"
    ]
    assert result["recommendation"].startswith("Run a network")


def test_invalid_json():
    result = normalize("this is not valid JSON")

    assert result["parse_error"] is True
    assert result["root_cause"] == ""
    assert result["evidence"] == []
    assert result["impact"] == []
    assert result["risk"] == "UNKNOWN"
    assert result["recommendation"] == ""
    assert result["confidence"] == 0.0


def test_confidence_clamped():
    high = normalize(json.dumps({
        "confidence": 5
    }))

    low = normalize(json.dumps({
        "confidence": -5
    }))

    assert high["confidence"] == 1.0
    assert low["confidence"] == 0.0


def test_empty_response():
    result = normalize("")

    assert result["parse_error"] is True
    assert result["confidence"] == 0.0
    assert result["risk"] == "UNKNOWN"
