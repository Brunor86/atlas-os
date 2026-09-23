from types import SimpleNamespace

from atlas.core.asset import (
    AssetStatus,
    AssetType,
)
from atlas.models.event import Event
from atlas.models.health import HealthInfo
from atlas.services.context.service import (
    ContextService,
)
from atlas.services.health.docker_rule import (
    DockerRule,
)
from atlas.services.noc.rules.event_rule import (
    EventRule,
)


def docker_asset():

    return SimpleNamespace(
        id=(
            "application-docker-"
            "nginx-proxy-manager"
        ),
        name="nginx-proxy-manager",
        type=AssetType.APPLICATION,
        status=AssetStatus.OFFLINE,
        metadata={
            "runtime":
                "docker",

            "container_name":
                "nginx-proxy-manager",

            "docker_status":
                "exited",

            "image":
                "test/image:latest",
        },
    )


def test_docker_rule_uses_current_asset_contract():

    asset = docker_asset()

    health = HealthInfo(
        status="healthy"
    )

    DockerRule().evaluate(
        infra=None,
        health=health,
        assets=[
            asset
        ],
    )

    assert health.status == "warning"

    assert len(
        health.alerts
    ) == 1

    alert = health.alerts[0]

    assert alert.source == "docker"

    assert alert.affected_assets == [
        asset.id
    ]


def test_context_projects_exact_affected_asset():

    asset = docker_asset()

    health = HealthInfo(
        status="healthy"
    )

    DockerRule().evaluate(
        infra=None,
        health=health,
        assets=[
            asset
        ],
    )

    service = ContextService.__new__(
        ContextService
    )

    events = service._events_from_health(
        health,
        [
            asset
        ],
    )

    assert len(
        events
    ) == 1

    event = events[0]

    assert event.asset_id == asset.id

    assert event.status == "active"

    assert (
        event.data["container"]
        == "nginx-proxy-manager"
    )

    assert (
        event.data["status"]
        == "exited"
    )


def test_context_does_not_rediscover_failure():

    asset = docker_asset()

    health = HealthInfo(
        status="healthy"
    )

    DockerRule().evaluate(
        infra=None,
        health=health,
        assets=[
            asset
        ],
    )

    #
    # Detection already happened.
    # Remove runtime state afterward.
    #
    asset.metadata.pop(
        "docker_status"
    )

    service = ContextService.__new__(
        ContextService
    )

    events = service._events_from_health(
        health,
        [
            asset
        ],
    )

    assert [
        event.asset_id
        for event in events
    ] == [
        asset.id
    ]


def test_event_rule_accepts_active_case_insensitively():

    rule = EventRule()

    for status in (
        "active",
        "ACTIVE",
        "Active",
    ):

        event = Event(
            type="TEST",
            title="Container stopped",
            message="container stopped",
            first_seen="",
            last_seen="",
            status=status,
        )

        signals = rule.evaluate(
            [
                event
            ]
        )

        assert len(
            signals
        ) == 1


def test_context_preserves_critical_alert_severity():

    health = HealthInfo(
        status="critical"
    )

    from atlas.models.alert import Alert

    health.alerts.append(
        Alert(
            severity="critical",
            source="storage",
            title="Storage Critical",
            message="Disk failure",
            affected_assets=[
                "disk:test"
            ],
        )
    )

    asset = SimpleNamespace(
        id="disk:test",
        name="disk-test",
        metadata={},
    )

    service = ContextService.__new__(
        ContextService
    )

    events = service._events_from_health(
        health,
        [
            asset
        ],
    )

    assert len(events) == 1

    event = events[0]

    assert event.status == "active"
    assert event.severity == "critical"
    assert event.asset_id == "disk:test"

    signals = EventRule().evaluate(
        events
    )

    assert len(signals) == 1

    assert (
        signals[0]["severity"]
        == "critical"
    )

    assert (
        signals[0]["impact"]
        == 60
    )


def test_context_preserves_warning_alert_severity_compatibility_path():

    health = HealthInfo(
        status="warning"
    )

    from atlas.models.alert import Alert

    health.alerts.append(
        Alert(
            severity="warning",
            source="system",
            title="System Warning",
            message="Synthetic warning",
        )
    )

    service = ContextService.__new__(
        ContextService
    )

    events = service._events_from_health(
        health,
        []
    )

    assert len(events) == 1

    event = events[0]

    assert event.status == "active"
    assert event.severity == "warning"
    assert event.asset_id == "system"

    signals = EventRule().evaluate(
        events
    )

    assert len(signals) == 1

    assert (
        signals[0]["severity"]
        == "warning"
    )

    assert (
        signals[0]["impact"]
        == 35
    )
