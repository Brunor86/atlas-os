from atlas.models.intelligence import IntelligenceResult


def test_intelligence_result_preserves_structured_diagnoses():

    diagnoses = [
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
    ]

    result = IntelligenceResult(
        state="DEGRADED",
        diagnoses=diagnoses,
    )

    data = result.to_dict()

    assert data["diagnoses"] == diagnoses

    assert len(data["diagnoses"]) == 2

    assert data["diagnoses"][0]["type"] == "DNS_FAILURE"

    assert data["diagnoses"][1]["type"] == "HIGH_TEMPERATURE"
