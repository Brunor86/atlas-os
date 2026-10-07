from datetime import (
    datetime,
    timezone,
)

import pytest

from atlas.services.sentinel import (
    SentinelEngine,
    SentinelFinding,
    SentinelSeverity,
    SentinelState,
    sentinel_fingerprint,
)


NOW = datetime(
    2026,
    10,
    7,
    2,
    0,
    tzinfo=timezone.utc,
)


def finding(
    severity=SentinelSeverity.WARNING,
    *,
    fingerprint="finding-1",
    state=SentinelState.OPEN,
    title="Storage degraded",
):
    return SentinelFinding(
        fingerprint=fingerprint,
        source="infrastructure",
        kind="storage_degradation",
        subject="disk-12tb",
        severity=severity,
        state=state,
        title=title,
        summary="Storage health is degraded.",
        observed_at=NOW,
        evidence={
            "health": 70,
        },
    )


def test_new_warning_notifies():
    result = SentinelEngine().evaluate(
        [
            finding(
                SentinelSeverity.WARNING
            )
        ],
        {},
        observed_at=NOW,
    )

    assert len(
        result.notifications
    ) == 1

    assert (
        result.notifications[0].reason
        == "new_warning"
    )


def test_new_critical_notifies():
    result = SentinelEngine().evaluate(
        [
            finding(
                SentinelSeverity.CRITICAL
            )
        ],
        {},
        observed_at=NOW,
    )

    assert len(
        result.notifications
    ) == 1

    assert (
        result.notifications[0].reason
        == "new_critical"
    )


def test_new_info_is_silent():
    result = SentinelEngine().evaluate(
        [
            finding(
                SentinelSeverity.INFO
            )
        ],
        {},
        observed_at=NOW,
    )

    assert not result.notifications


def test_repeated_warning_does_not_spam():
    previous = finding(
        SentinelSeverity.WARNING
    )

    current = finding(
        SentinelSeverity.WARNING
    )

    result = SentinelEngine().evaluate(
        [current],
        {
            previous.fingerprint:
                previous,
        },
        observed_at=NOW,
    )

    assert not result.notifications


def test_warning_to_critical_notifies_escalation():
    previous = finding(
        SentinelSeverity.WARNING
    )

    current = finding(
        SentinelSeverity.CRITICAL
    )

    result = SentinelEngine().evaluate(
        [current],
        {
            previous.fingerprint:
                previous,
        },
        observed_at=NOW,
    )

    assert len(
        result.notifications
    ) == 1

    assert (
        result.notifications[0].reason
        == "severity_escalated"
    )


def test_disappearing_warning_generates_recovery_once():
    previous = finding(
        SentinelSeverity.WARNING
    )

    result = SentinelEngine().evaluate(
        [],
        {
            previous.fingerprint:
                previous,
        },
        observed_at=NOW,
    )

    assert len(
        result.recoveries
    ) == 1

    recovered = (
        result.recoveries[0]
    )

    assert (
        recovered.state
        == SentinelState.RECOVERED
    )

    assert len(
        result.notifications
    ) == 1

    assert (
        result.notifications[0].reason
        == "recovered"
    )


def test_recovered_condition_does_not_notify_repeatedly():
    previous = finding(
        SentinelSeverity.WARNING
    ).recovered(
        observed_at=NOW
    )

    result = SentinelEngine().evaluate(
        [],
        {
            previous.fingerprint:
                previous,
        },
        observed_at=NOW,
    )

    assert not result.notifications

    assert (
        result.next_state[
            previous.fingerprint
        ].state
        == SentinelState.RECOVERED
    )


def test_reappearing_warning_notifies():
    previous = finding(
        SentinelSeverity.WARNING
    ).recovered(
        observed_at=NOW
    )

    current = finding(
        SentinelSeverity.WARNING
    )

    result = SentinelEngine().evaluate(
        [current],
        {
            previous.fingerprint:
                previous,
        },
        observed_at=NOW,
    )

    assert len(
        result.notifications
    ) == 1

    assert (
        result.notifications[0].reason
        == "reopened"
    )


def test_fingerprint_is_normalized_and_stable():
    first = sentinel_fingerprint(
        source=" Infrastructure ",
        kind="Storage   Degradation",
        subject=" DISK-12TB ",
    )

    second = sentinel_fingerprint(
        source="infrastructure",
        kind="storage degradation",
        subject="disk-12tb",
    )

    assert first == second


def test_fingerprint_changes_for_different_subject():
    first = sentinel_fingerprint(
        source="infrastructure",
        kind="storage_degradation",
        subject="disk-a",
    )

    second = sentinel_fingerprint(
        source="infrastructure",
        kind="storage_degradation",
        subject="disk-b",
    )

    assert first != second


def test_duplicate_fingerprint_is_rejected():
    one = finding(
        fingerprint="same"
    )

    two = finding(
        fingerprint="same"
    )

    with pytest.raises(
        ValueError,
        match="duplicate Sentinel fingerprint",
    ):
        SentinelEngine().evaluate(
            [
                one,
                two,
            ],
            {},
            observed_at=NOW,
        )
