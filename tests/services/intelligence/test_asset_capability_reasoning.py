from atlas.services.intelligence.reasoning.service import (
    IntelligenceReasoner,
)


def make_asset_context(
    status="ONLINE",
    health=100.0,
    capabilities=None,
):
    return {
        "asset": {
            "id": "asset-test",
            "name": "jellyseerr",
            "type": "APPLICATION",
            "status": status,
            "health": health,
            "roles": ["MEDIA_SERVER"],
            "capabilities": capabilities or [],
        },
        "identity": {
            "vendor": "Docker",
            "model": "fallenbagel/jellyseerr:latest",
        },
        "metadata": {},
        "observations": [],
        "relationships": [],
    }


def test_online_healthy_asset_has_no_action():
    reasoner = IntelligenceReasoner()

    result = reasoner.reason(
        insights=[],
        context={"health": "healthy"},
        asset_context=make_asset_context(
            status="ONLINE",
            health=100.0,
            capabilities=[
                "START",
                "STOP",
                "RESTART",
                "LOGS",
            ],
        ),
    )

    assert result["state"] == "HEALTHY"
    assert result["recommended_actions"] == []


def test_offline_asset_with_restart_recommends_restart():
    reasoner = IntelligenceReasoner()

    result = reasoner.reason(
        insights=[],
        context={"health": "healthy"},
        asset_context=make_asset_context(
            status="OFFLINE",
            health=0.0,
            capabilities=[
                "START",
                "STOP",
                "RESTART",
                "LOGS",
            ],
        ),
    )

    assert result["state"] == "CRITICAL"

    actions = result["recommended_actions"]

    assert len(actions) == 1
    assert actions[0]["action"] == "restart asset"
    assert actions[0]["asset_id"] == "asset-test"


def test_offline_asset_with_only_start_recommends_start():
    reasoner = IntelligenceReasoner()

    result = reasoner.reason(
        insights=[],
        context={"health": "healthy"},
        asset_context=make_asset_context(
            status="OFFLINE",
            health=0.0,
            capabilities=[
                "START",
                "LOGS",
            ],
        ),
    )

    actions = result["recommended_actions"]

    assert len(actions) == 1
    assert actions[0]["action"] == "start asset"


def test_offline_asset_without_start_or_restart_has_no_action():
    reasoner = IntelligenceReasoner()

    result = reasoner.reason(
        insights=[],
        context={"health": "healthy"},
        asset_context=make_asset_context(
            status="OFFLINE",
            health=0.0,
            capabilities=[
                "LOGS",
            ],
        ),
    )

    assert result["state"] == "CRITICAL"
    assert result["recommended_actions"] == []


def test_degraded_asset_with_logs_recommends_diagnosis():
    reasoner = IntelligenceReasoner()

    result = reasoner.reason(
        insights=[],
        context={"health": "healthy"},
        asset_context=make_asset_context(
            status="ONLINE",
            health=65.0,
            capabilities=[
                "LOGS",
            ],
        ),
    )

    assert result["state"] == "WARNING"

    actions = result["recommended_actions"]

    assert len(actions) == 1
    assert actions[0]["action"] == "inspect asset logs"
    assert actions[0]["asset_id"] == "asset-test"


def test_degraded_asset_without_logs_has_no_diagnostic_action():
    reasoner = IntelligenceReasoner()

    result = reasoner.reason(
        insights=[],
        context={"health": "healthy"},
        asset_context=make_asset_context(
            status="ONLINE",
            health=65.0,
            capabilities=[],
        ),
    )

    assert result["state"] == "WARNING"
    assert result["recommended_actions"] == []
