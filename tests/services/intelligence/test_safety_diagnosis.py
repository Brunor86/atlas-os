from types import SimpleNamespace

from atlas.services.intelligence.safety.service import (
    ActionSafetyService,
)


def make_incident(
    action,
    diagnosis,
    risk="LOW",
):

    return SimpleNamespace(
        incident_id="INC-TEST",
        asset="test-asset",
        recommendation={
            "action": action,
            "risk": risk,
            "incident_id": "INC-TEST",
            "diagnosis": diagnosis,
            "evidence": [],
        },
    )


def test_diagnosis_inspection_is_safe():

    service = ActionSafetyService()

    incident = make_incident(
        action="inspect logs",
        diagnosis={
            "type": "DNS_FAILURE",
            "category": "NETWORK",
            "confidence": 0.95,
        },
    )

    result = service.evaluate(
        incident
    )

    assert result["action"] == "inspect logs"

    assert result["requires_approval"] is True

    assert result["status"] == "PENDING_APPROVAL"


def test_critical_storage_restart_requires_block():

    service = ActionSafetyService()

    incident = make_incident(
        action="restart",
        risk="HIGH",
        diagnosis={
            "type": "STORAGE_HEALTH_FAILURE",
            "category": "STORAGE",
            "confidence": 0.98,
        },
    )

    result = service.evaluate(
        incident
    )

    assert result["status"] == "BLOCKED"

    assert result["requires_approval"] is False


def test_high_temperature_inspection_is_allowed():

    service = ActionSafetyService()

    incident = make_incident(
        action="inspect temperature",
        diagnosis={
            "type": "HIGH_TEMPERATURE",
            "category": "THERMAL",
            "confidence": 0.80,
        },
    )

    result = service.evaluate(
        incident
    )

    assert result["action"] == "inspect temperature"

    assert result["requires_approval"] is True

    assert result["status"] == "PENDING_APPROVAL"
