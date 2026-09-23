from types import SimpleNamespace

from atlas.services.incidents.lifecycle import (
    IncidentLifecycle,
)
from atlas.services.noc.service import (
    NOCService,
)
from atlas.storage.database import Database


class RecordingRepository:

    def __init__(self):

        self.saved = []
        self.seen = set()

    def has_fingerprint(
        self,
        incident_id,
        state,
        fingerprint,
    ):

        return (
            incident_id,
            state,
            fingerprint,
        ) in self.seen

    def save(
        self,
        event,
    ):

        self.saved.append(
            dict(event)
        )

        fingerprint = event.get(
            "fingerprint"
        )

        if fingerprint:

            self.seen.add(
                (
                    event["incident_id"],
                    event["state"],
                    fingerprint,
                )
            )


def incident():

    return SimpleNamespace(
        id="internal-id",
        incident_id="INC-0001",
        lifecycle=[],
    )


def test_same_material_transition_is_persisted_once():

    repository = RecordingRepository()

    lifecycle = IncidentLifecycle(
        repository
    )

    item = incident()

    lifecycle.transition(
        item,
        "RECOMMENDED",
        "Operational recommendation generated",
        fingerprint="same-state",
    )

    lifecycle.transition(
        item,
        "RECOMMENDED",
        "Operational recommendation generated",
        fingerprint="same-state",
    )

    assert len(
        repository.saved
    ) == 1

    assert len(
        item.lifecycle
    ) == 1


def test_changed_material_transition_is_persisted():

    repository = RecordingRepository()

    lifecycle = IncidentLifecycle(
        repository
    )

    item = incident()

    lifecycle.transition(
        item,
        "DIAGNOSED",
        "Root cause identified",
        fingerprint="state-a",
    )

    lifecycle.transition(
        item,
        "DIAGNOSED",
        "Root cause identified",
        fingerprint="state-b",
    )

    assert len(
        repository.saved
    ) == 2


def test_non_fingerprinted_transition_keeps_append_only_behavior():

    repository = RecordingRepository()

    lifecycle = IncidentLifecycle(
        repository
    )

    item = incident()

    lifecycle.transition(
        item,
        "PENDING_APPROVAL",
        "Action requires operator approval",
    )

    lifecycle.transition(
        item,
        "PENDING_APPROVAL",
        "Action requires operator approval",
    )

    assert len(
        repository.saved
    ) == 2


def test_noc_fingerprint_ignores_volatile_timestamps():

    first = SimpleNamespace(
        name="service_degradation",
        asset="application-docker-test",
        severity="MEDIUM",
        events=[
            {
                "title": "Docker",
                "asset_id": "asset-1",
                "last_seen": "one",
            }
        ],
        impact=["asset-1"],
        root_cause="container unhealthy",
        diagnosis="restart candidate",
        blast_radius=[],
        suggested_actions=["restart"],
        recommendation={
            "action": "restart",
            "generated_at": "one",
        },
        decision={
            "action": "restart",
            "generated_at": "one",
        },
        safe_action={},
    )

    second = SimpleNamespace(
        **{
            **vars(first),
            "events": [
                {
                    "title": "Docker",
                    "asset_id": "asset-1",
                    "last_seen": "two",
                }
            ],
            "recommendation": {
                "action": "restart",
                "generated_at": "two",
            },
            "decision": {
                "action": "restart",
                "generated_at": "two",
            },
        }
    )

    assert (
        NOCService._lifecycle_fingerprint(
            first,
            "RECOMMENDED",
        )
        ==
        NOCService._lifecycle_fingerprint(
            second,
            "RECOMMENDED",
        )
    )


def test_noc_fingerprint_changes_with_material_diagnosis():

    first = SimpleNamespace(
        name="service_degradation",
        asset="application-docker-test",
        severity="MEDIUM",
        events=[],
        impact=[],
        root_cause="cause-a",
        diagnosis="diagnosis-a",
        blast_radius=[],
        suggested_actions=[],
        recommendation={},
        decision={},
        safe_action={},
    )

    second = SimpleNamespace(
        **{
            **vars(first),
            "diagnosis": "diagnosis-b",
        }
    )

    assert (
        NOCService._lifecycle_fingerprint(
            first,
            "DIAGNOSED",
        )
        !=
        NOCService._lifecycle_fingerprint(
            second,
            "DIAGNOSED",
        )
    )


def test_database_has_lifecycle_fingerprint_column():

    database = Database()

    try:

        columns = {
            row[1]
            for row in database.conn.execute(
                """
                PRAGMA table_info(
                    incident_lifecycle_events
                )
                """
            ).fetchall()
        }

        assert (
            "fingerprint"
            in columns
        )

    finally:

        database.close()
