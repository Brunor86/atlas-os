from atlas.models.event import Event

from atlas.services.noc.rules.event_rule import (
    EventRule,
)


def make_event(
    status,
    *,
    severity="warning",
    title="Docker",
    message="Container failure",
    asset_id=None,
):

    return Event(
        type=severity,
        title=title,
        message=message,
        first_seen="2026-09-20T00:00:00",
        last_seen="2026-09-20T00:00:00",
        status=status,
        severity=severity,
        asset_id=asset_id,
    )


def test_open_warning_generates_warning_signal():

    signals = EventRule().evaluate(
        [
            make_event(
                "open",
                severity="warning",
                asset_id="container:test",
            )
        ]
    )

    assert len(signals) == 1

    signal = signals[0]

    assert signal["source"] == "event"
    assert signal["impact"] == 35
    assert signal["severity"] == "warning"

    assert (
        signal["message"]
        == "Docker: Container failure"
    )

    assert (
        signal["asset_id"]
        == "container:test"
    )


def test_open_critical_generates_critical_signal():

    signals = EventRule().evaluate(
        [
            make_event(
                "open",
                severity="critical",
                title="Storage",
                message="Disk failure",
            )
        ]
    )

    assert len(signals) == 1

    assert signals[0]["impact"] == 60

    assert (
        signals[0]["severity"]
        == "critical"
    )


def test_open_info_does_not_generate_signal():

    signals = EventRule().evaluate(
        [
            make_event(
                "open",
                severity="info",
                title="Infrastructure Healthy",
                message=(
                    "No critical issues were detected."
                ),
            )
        ]
    )

    assert signals == []


def test_closed_warning_does_not_generate_signal():

    signals = EventRule().evaluate(
        [
            make_event(
                "closed",
                severity="warning",
            )
        ]
    )

    assert signals == []


def test_closed_critical_does_not_generate_signal():

    signals = EventRule().evaluate(
        [
            make_event(
                "closed",
                severity="critical",
            )
        ]
    )

    assert signals == []


def test_status_and_severity_are_normalized():

    signals = EventRule().evaluate(
        [
            make_event(
                "  OPEN  ",
                severity=" WARNING ",
            )
        ]
    )

    assert len(signals) == 1
    assert signals[0]["impact"] == 35
    assert signals[0]["severity"] == "warning"


def test_health_projection_active_warning_generates_signal():

    signals = EventRule().evaluate(
        [
            make_event(
                "active",
                severity="warning",
            )
        ]
    )

    assert len(signals) == 1
    assert signals[0]["impact"] == 35
    assert signals[0]["severity"] == "warning"


def test_only_actionable_open_events_generate_signals():

    signals = EventRule().evaluate(
        [
            make_event(
                "open",
                severity="info",
                title="Healthy",
            ),
            make_event(
                "open",
                severity="warning",
                title="Warning",
            ),
            make_event(
                "open",
                severity="critical",
                title="Critical",
            ),
            make_event(
                "closed",
                severity="critical",
                title="Old critical",
            ),
        ]
    )

    assert len(signals) == 2

    assert [
        signal["severity"]
        for signal in signals
    ] == [
        "warning",
        "critical",
    ]

    assert [
        signal["impact"]
        for signal in signals
    ] == [
        35,
        60,
    ]


def test_health_projection_active_info_does_not_generate_signal():

    signals = EventRule().evaluate(
        [
            make_event(
                "active",
                severity="info",
                title="Healthy projection",
            )
        ]
    )

    assert signals == []
