from datetime import datetime, timezone

from atlas.services.intelligence.reasoning.service import (
    IntelligenceReasoner,
)


def make_asset_context(
    *,
    name="jellyseerr",
    status="ONLINE",
    health=65.0,
    capabilities=None,
    observations=None,
):

    return {
        "asset": {
            "id": "asset-1",
            "name": name,
            "type": "APPLICATION",
            "status": status,
            "health": health,
            "criticality": "MEDIUM",
            "roles": ["MEDIA_SERVER"],
            "capabilities": capabilities or [],
        },
        "identity": {
            "vendor": "Docker",
            "model": "fallenbagel/jellyseerr:latest",
        },
        "observations": observations or [],
        "relationships": [],
    }


def make_observation(
    *,
    type,
    value,
    severity,
    source="docker",
):

    return {
        "type": type,
        "value": value,
        "severity": severity,
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def test_warning_observation_is_added_to_reasoning():

    reasoner = IntelligenceReasoner()

    result = reasoner.reason(
        insights=[],
        context={"health": "healthy"},
        asset_context=make_asset_context(
            observations=[
                make_observation(
                    type="dns",
                    value="resolution failed",
                    severity="WARNING",
                ),
            ],
        ),
    )

    assert result["state"] == "WARNING"

    assert any(
        "dns" in item.lower()
        for item in result["reasoning"]
    )


def test_critical_observation_makes_asset_critical():

    reasoner = IntelligenceReasoner()

    result = reasoner.reason(
        insights=[],
        context={"health": "healthy"},
        asset_context=make_asset_context(
            health=100.0,
            observations=[
                make_observation(
                    type="smart",
                    value="FAILED",
                    severity="CRITICAL",
                    source="smart",
                ),
            ],
        ),
    )

    assert result["state"] == "CRITICAL"

    assert any(
        "critical" in item.lower()
        for item in result["risks"]
    )


def test_degraded_asset_with_observation_and_logs_recommends_diagnosis():

    reasoner = IntelligenceReasoner()

    result = reasoner.reason(
        insights=[],
        context={"health": "healthy"},
        asset_context=make_asset_context(
            health=65.0,
            capabilities=["LOGS"],
            observations=[
                make_observation(
                    type="dns",
                    value="resolution failed",
                    severity="WARNING",
                ),
            ],
        ),
    )

    assert result["state"] == "WARNING"

    actions = result["recommended_actions"]

    assert len(actions) == 1

    action = actions[0]

    assert action["action"] == "inspect logs"

    assert action["asset_id"] == "asset-1"

    assert action["risk"] == "LOW"


def test_critical_smart_failure_recommends_diagnosis_before_restart():

    reasoner = IntelligenceReasoner()

    result = reasoner.reason(
        insights=[],
        context={"health": "healthy"},
        asset_context=make_asset_context(
            status="ONLINE",
            health=100.0,
            capabilities=["LOGS", "RESTART"],
            observations=[
                make_observation(
                    type="smart",
                    value="FAILED",
                    severity="CRITICAL",
                    source="smart",
                ),
            ],
        ),
    )

    assert result["state"] == "CRITICAL"

    actions = result["recommended_actions"]

    assert len(actions) == 1

    assert actions[0]["action"] == "inspect logs"


def test_info_observation_does_not_change_healthy_state():

    reasoner = IntelligenceReasoner()

    result = reasoner.reason(
        insights=[],
        context={"health": "healthy"},
        asset_context=make_asset_context(
            status="ONLINE",
            health=100.0,
            observations=[
                make_observation(
                    type="smart",
                    value="PASSED",
                    severity="INFO",
                    source="smart",
                ),
            ],
        ),
    )

    assert result["state"] == "HEALTHY"

    assert not result["risks"]



def test_observation_driven_action_preserves_evidence():

    reasoner = IntelligenceReasoner()

    result = reasoner.reason(
        insights=[],
        context={"health": "healthy"},
        asset_context=make_asset_context(
            health=65.0,
            capabilities=["LOGS"],
            observations=[
                make_observation(
                    type="dns",
                    value="resolution failed",
                    severity="WARNING",
                    source="docker",
                ),
            ],
        ),
    )

    actions = result["recommended_actions"]

    assert len(actions) == 1

    action = actions[0]

    assert action["action"] == "inspect logs"

    assert action["asset_id"] == "asset-1"

    assert action["risk"] == "LOW"

    assert action["evidence"]["type"] == "dns"

    assert action["evidence"]["value"] == "resolution failed"

    assert action["evidence"]["severity"] == "WARNING"

    assert action["evidence"]["source"] == "docker"


def test_multiple_observations_are_preserved_in_reasoning():

    reasoner = IntelligenceReasoner()

    result = reasoner.reason(
        insights=[],
        context={"health": "healthy"},
        asset_context=make_asset_context(
            observations=[
                make_observation(
                    type="temperature",
                    value=55,
                    severity="WARNING",
                    source="smart",
                ),
                make_observation(
                    type="dns",
                    value="resolution failed",
                    severity="WARNING",
                    source="docker",
                ),
            ],
        ),
    )

    assert result["state"] == "WARNING"

    reasoning = " ".join(
        result["reasoning"]
    ).lower()

    assert "temperature" in reasoning
    assert "dns" in reasoning

def test_dns_observation_produces_structured_diagnosis():

    reasoner = IntelligenceReasoner()

    result = reasoner.reason(
        insights=[],
        context={"health": "healthy"},
        asset_context=make_asset_context(
            observations=[
                make_observation(
                    type="dns",
                    value="resolution failed",
                    severity="WARNING",
                    source="docker",
                ),
            ],
        ),
    )

    diagnoses = result["diagnoses"]

    assert len(diagnoses) == 1

    diagnosis = diagnoses[0]

    assert diagnosis["type"] == "DNS_FAILURE"

    assert diagnosis["category"] == "NETWORK"

    assert diagnosis["confidence"] == 0.95

    assert (
        diagnosis["evidence"]["value"]
        == "resolution failed"
    )


def test_smart_failure_produces_storage_diagnosis():

    reasoner = IntelligenceReasoner()

    result = reasoner.reason(
        insights=[],
        context={"health": "healthy"},
        asset_context=make_asset_context(
            health=100.0,
            observations=[
                make_observation(
                    type="smart",
                    value="FAILED",
                    severity="CRITICAL",
                    source="smart",
                ),
            ],
        ),
    )

    diagnoses = result["diagnoses"]

    assert len(diagnoses) == 1

    diagnosis = diagnoses[0]

    assert (
        diagnosis["type"]
        == "STORAGE_HEALTH_FAILURE"
    )

    assert diagnosis["category"] == "STORAGE"

    assert diagnosis["confidence"] == 0.98


def test_temperature_observation_produces_thermal_diagnosis():

    reasoner = IntelligenceReasoner()

    result = reasoner.reason(
        insights=[],
        context={"health": "healthy"},
        asset_context=make_asset_context(
            observations=[
                make_observation(
                    type="temperature",
                    value=55,
                    severity="WARNING",
                    source="smart",
                ),
            ],
        ),
    )

    diagnoses = result["diagnoses"]

    assert len(diagnoses) == 1

    diagnosis = diagnoses[0]

    assert diagnosis["type"] == "HIGH_TEMPERATURE"

    assert diagnosis["category"] == "THERMAL"

    assert diagnosis["confidence"] == 0.80
