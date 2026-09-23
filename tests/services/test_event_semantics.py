from dataclasses import asdict

from atlas.models.insight import Insight
from atlas.services.events.correlation import EventCorrelation
from atlas.services.events.service import EventService
from atlas.services.noc.service import normalize_events


class FakeEventDatabase:

    def __init__(
        self,
        active=None,
    ):

        self.active = list(
            active
            or []
        )

        self.saved = []
        self.refreshed = []
        self.closed = []


    def get_active_events(
        self,
    ):

        return list(
            self.active
        )


    def save_event(
        self,
        *args,
    ):

        self.saved.append(
            args
        )


    def refresh_event(
        self,
        *args,
    ):

        self.refreshed.append(
            args
        )


    def close_event(
        self,
        *args,
    ):

        self.closed.append(
            args
        )


def make_service(
    database,
):

    service = object.__new__(
        EventService
    )

    service.database = database

    return service


def test_info_insight_preserves_event_semantics():

    database = FakeEventDatabase()

    service = make_service(
        database
    )


    insight = Insight(
        title="Infrastructure Healthy",
        summary=(
            "No critical issues were detected."
        ),
        severity="info",
    )


    service.process(
        [insight]
    )


    assert len(
        database.saved
    ) == 1


    saved = database.saved[0]


    assert saved[0] == "info"
    assert saved[1] == "Infrastructure Healthy"

    assert (
        saved[2]
        == "No critical issues were detected."
    )

    assert saved[7] == "info"

    assert (
        saved[6]
        == "infrastructure_healthy"
    )


def test_existing_event_metadata_self_heals():

    database = FakeEventDatabase(
        [
            {
                "id": 4,
                "type": "unknown",
                "title": "Docker",
                "message": "",
                "first_seen": "old",
                "last_seen": "old",
                "status": "open",
                "event_key": "docker",
                "severity": "warning",
                "category": "docker",
                "occurrences": 10,
                "asset_id": "stale-asset",
            }
        ]
    )

    service = make_service(
        database
    )


    insight = Insight(
        title="Docker",
        summary=(
            "All containers are running."
        ),
        severity="info",
        asset_id=None,
    )


    service.process(
        [insight]
    )


    assert database.saved == []

    assert len(
        database.refreshed
    ) == 1


    refreshed = (
        database.refreshed[0]
    )


    assert refreshed[0] == 4
    assert refreshed[1] == "info"
    assert refreshed[2] == "Docker"

    assert (
        refreshed[3]
        == "All containers are running."
    )

    assert refreshed[5] == "info"
    assert refreshed[6] == "docker"

    # Healthy Docker observation must clear
    # the previously affected asset.
    assert refreshed[7] is None


def test_normalize_events_preserves_severity():

    normalized = normalize_events(
        [
            {
                "type": "info",
                "title":
                    "Infrastructure Healthy",
                "message":
                    "No critical issues were detected.",
                "first_seen": "a",
                "last_seen": "b",
                "status": "open",
                "severity": "info",
                "asset_id": None,
            }
        ]
    )


    assert len(
        normalized
    ) == 1

    assert (
        normalized[0].severity
        == "info"
    )


def test_healthy_infrastructure_does_not_correlate_as_degradation():

    events = [
        asdict(
            Insight(
                title=
                    "Infrastructure Healthy",
                summary=
                    "No critical issues were detected.",
                severity="info",
            )
        ),
        asdict(
            Insight(
                title="Docker",
                summary=
                    "All containers are running.",
                severity="info",
            )
        ),
    ]


    incidents = (
        EventCorrelation()
        .analyze(
            events
        )
    )


    assert not any(
        incident.get("name")
        == "infrastructure_degradation"

        for incident
        in incidents
    )


def test_warning_infrastructure_still_correlates_as_degradation():

    events = [
        asdict(
            Insight(
                title=
                    "Infrastructure Warning",
                summary=
                    (
                        "The infrastructure is "
                        "operational but requires "
                        "attention."
                    ),
                severity="warning",
            )
        ),
        asdict(
            Insight(
                title="Docker",
                summary=
                    "1 container is stopped.",
                severity="warning",
                asset_id="container-1",
            )
        ),
    ]


    incidents = (
        EventCorrelation()
        .analyze(
            events
        )
    )


    assert any(
        incident.get("name")
        == "infrastructure_degradation"

        for incident
        in incidents
    )


def test_legacy_infrastructure_health_warning_remains_supported():

    events = [
        {
            "title":
                "Infrastructure health",

            "summary":
                "Current state: warning",

            "severity":
                "warning",
        },

        {
            "title":
                "Docker",

            "summary":
                "1 container is stopped.",

            "severity":
                "warning",
        },
    ]


    incidents = (
        EventCorrelation()
        .analyze(
            events
        )
    )


    assert any(
        incident.get("name")
        == "infrastructure_degradation"

        for incident
        in incidents
    )
