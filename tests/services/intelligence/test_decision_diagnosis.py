from atlas.services.intelligence.decision.service import (
    IntelligenceDecisionService,
)


def test_dns_failure_produces_diagnostic_decision():

    service = IntelligenceDecisionService()

    reasoning = {
        "state": "DEGRADED",
        "diagnoses": [
            {
                "type": "DNS_FAILURE",
                "category": "NETWORK",
                "confidence": 0.95,
                "evidence": {
                    "observation_type": "dns",
                    "value": "resolution failed",
                    "severity": "WARNING",
                    "source": "docker",
                },
            },
        ],
        "recommended_actions": [],
    }

    decision = service.build(
        reasoning=reasoning,
    )

    assert decision["diagnoses"]

    assert decision["diagnoses"][0]["type"] == "DNS_FAILURE"

    assert decision["diagnosis"]["type"] == "DNS_FAILURE"

    assert decision["action"] == "inspect logs"

    assert decision["risk"] == "LOW"

    assert decision["source"] == "diagnosis"


def test_storage_failure_does_not_recommend_restart():

    service = IntelligenceDecisionService()

    reasoning = {
        "state": "CRITICAL",
        "diagnoses": [
            {
                "type": "STORAGE_HEALTH_FAILURE",
                "category": "STORAGE",
                "confidence": 0.98,
                "evidence": {
                    "observation_type": "smart",
                    "value": "FAILED",
                    "severity": "CRITICAL",
                    "source": "smart",
                },
            },
        ],
        "recommended_actions": [],
    }

    decision = service.build(
        reasoning=reasoning,
    )

    assert decision["diagnosis"]["type"] == (
        "STORAGE_HEALTH_FAILURE"
    )

    assert decision["action"] == "inspect SMART"

    assert decision["risk"] == "HIGH"

    assert decision["source"] == "diagnosis"


def test_high_temperature_recommends_inspection():

    service = IntelligenceDecisionService()

    reasoning = {
        "state": "DEGRADED",
        "diagnoses": [
            {
                "type": "HIGH_TEMPERATURE",
                "category": "THERMAL",
                "confidence": 0.80,
                "evidence": {
                    "observation_type": "temperature",
                    "value": "75C",
                    "severity": "WARNING",
                    "source": "smart",
                },
            },
        ],
        "recommended_actions": [],
    }

    decision = service.build(
        reasoning=reasoning,
    )

    assert decision["diagnosis"]["type"] == (
        "HIGH_TEMPERATURE"
    )

    assert decision["action"] == "inspect temperature"

    assert decision["risk"] == "LOW"

    assert decision["source"] == "diagnosis"
