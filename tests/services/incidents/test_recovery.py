from datetime import (
    UTC,
    datetime,
    timedelta,
)

from types import SimpleNamespace

from atlas.models.incident import (
    Incident,
)

from atlas.services.incidents.manager import (
    IncidentManager,
)

from atlas.services.incidents.recovery import (
    IncidentRecoveryService,
)

from atlas.storage.action_repository import (
    ActionRepository,
)


NOW = datetime(
    2026,
    9,
    20,
    5,
    30,
    0,
    tzinfo=UTC,
)


def setup_runtime(
    tmp_path,
    monkeypatch,
):

    database = (
        tmp_path
        / "atlas.db"
    )

    monkeypatch.setenv(
        "ATLAS_DB_PATH",
        str(database),
    )

    manager = IncidentManager()

    actions = ActionRepository(
        manager.repository.database
    )

    recovery = IncidentRecoveryService(
        incident_manager=manager,
        action_repository=actions,
        clock=lambda: NOW,
    )

    return (
        manager,
        actions,
        recovery,
    )


def save_incident(
    manager,
    incident_id,
    *,
    status="OPEN",
    updated_at=None,
):

    incident = Incident(
        id=incident_id,
        title="service_degradation",
        asset="application:test",
        severity="MEDIUM",
        status=status,
        updated_at=(
            updated_at
            or NOW
        ),
    )

    incident.incident_id = (
        incident_id
    )

    manager.repository.save(
        incident
    )

    return incident


def save_action(
    repository,
    action_id,
    incident_id,
    status,
):

    repository.save_action_request(
        {
            "id":
                action_id,

            "incident_id":
                incident_id,

            "action":
                "restart container",

            "target":
                "test-container",

            "risk":
                "LOW",

            "rollback":
                "",

            "status":
                status,

            "created_at":
                NOW.isoformat(),

            "approved_by":
                (
                    "BRUNO"
                    if status
                    == "APPROVED"
                    else None
                ),

            "approved_at":
                (
                    NOW.isoformat()
                    if status
                    == "APPROVED"
                    else None
                ),

            "incident_fingerprint":
                None,
        }
    )


def status_of(
    manager,
    incident_id,
):

    return (
        manager.get_incident(
            incident_id
        ).status
    )


def test_open_absence_enters_recovering(
    tmp_path,
    monkeypatch,
):

    manager, actions, recovery = (
        setup_runtime(
            tmp_path,
            monkeypatch,
        )
    )

    save_incident(
        manager,
        "INC-0001",
    )

    result = recovery.reconcile(
        []
    )

    assert (
        status_of(
            manager,
            "INC-0001",
        )
        == "RECOVERING"
    )

    assert (
        result["transitions"]
        == [
            {
                "incident_id":
                    "INC-0001",

                "from":
                    "OPEN",

                "to":
                    "RECOVERING",

                "reason":
                    "CONDITION_ABSENT",

                "cancelled_actions":
                    0,
            }
        ]
    )


def test_recovering_requires_grace_period(
    tmp_path,
    monkeypatch,
):

    manager, actions, recovery = (
        setup_runtime(
            tmp_path,
            monkeypatch,
        )
    )

    save_incident(
        manager,
        "INC-0001",
        status="RECOVERING",
        updated_at=(
            NOW
            - timedelta(
                seconds=299
            )
        ),
    )

    result = recovery.reconcile(
        []
    )

    assert (
        status_of(
            manager,
            "INC-0001",
        )
        == "RECOVERING"
    )

    assert (
        result["transitions"]
        == []
    )


def test_recovering_resolves_after_grace(
    tmp_path,
    monkeypatch,
):

    manager, actions, recovery = (
        setup_runtime(
            tmp_path,
            monkeypatch,
        )
    )

    save_incident(
        manager,
        "INC-0001",
        status="RECOVERING",
        updated_at=(
            NOW
            - timedelta(
                seconds=300
            )
        ),
    )

    result = recovery.reconcile(
        []
    )

    assert (
        status_of(
            manager,
            "INC-0001",
        )
        == "RESOLVED"
    )

    assert (
        result["transitions"][0][
            "reason"
        ]
        == "RECOVERY_CONFIRMED"
    )


def test_reappearing_recovering_incident_returns_open(
    tmp_path,
    monkeypatch,
):

    manager, actions, recovery = (
        setup_runtime(
            tmp_path,
            monkeypatch,
        )
    )

    save_incident(
        manager,
        "INC-0001",
        status="RECOVERING",
        updated_at=(
            NOW
            - timedelta(
                seconds=120
            )
        ),
    )

    current = SimpleNamespace(
        incident_id="INC-0001"
    )

    result = recovery.reconcile(
        [
            current
        ]
    )

    assert (
        status_of(
            manager,
            "INC-0001",
        )
        == "OPEN"
    )

    assert (
        result["transitions"][0][
            "reason"
        ]
        == "CONDITION_REAPPEARED"
    )


def test_non_authoritative_cycle_never_changes_incident(
    tmp_path,
    monkeypatch,
):

    manager, actions, recovery = (
        setup_runtime(
            tmp_path,
            monkeypatch,
        )
    )

    save_incident(
        manager,
        "INC-0001",
    )

    result = recovery.reconcile(
        [],
        authoritative=False,
    )

    assert (
        status_of(
            manager,
            "INC-0001",
        )
        == "OPEN"
    )

    assert result == {
        "status":
            "SKIPPED",

        "reason":
            "NON_AUTHORITATIVE",

        "transitions":
            [],
    }


def test_recovery_cancels_only_definitely_unexecuted_actions(
    tmp_path,
    monkeypatch,
):

    manager, actions, recovery = (
        setup_runtime(
            tmp_path,
            monkeypatch,
        )
    )

    save_incident(
        manager,
        "INC-0001",
    )

    save_action(
        actions,
        "pending",
        "INC-0001",
        "PENDING_APPROVAL",
    )

    save_action(
        actions,
        "approved-ready",
        "INC-0001",
        "APPROVED",
    )

    save_action(
        actions,
        "approved-claimed",
        "INC-0001",
        "APPROVED",
    )

    assert (
        actions.claim_action_execution(
            "approved-claimed"
        )
        is True
    )


    result = recovery.reconcile(
        []
    )


    assert (
        result["transitions"][0][
            "cancelled_actions"
        ]
        == 2
    )


    assert (
        actions.get_action_request(
            "pending"
        )["status"]
        == "CANCELLED"
    )

    assert (
        actions.get_action_request(
            "approved-ready"
        )["status"]
        == "CANCELLED"
    )

    #
    # A durable execution claim means command outcome may
    # already be external/uncertain. Never rewrite it.
    #
    assert (
        actions.get_action_request(
            "approved-claimed"
        )["status"]
        == "APPROVED"
    )
