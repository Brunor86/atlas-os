from atlas.services.semantic.attention import (
    OperationalAttentionService,
)


class FakeHealthRepository:

    def __init__(
        self,
        findings=None,
    ):
        self.findings = (
            findings
            or []
        )

    def get_active(self):

        return list(
            self.findings
        )


class FakeIncidentRepository:

    def __init__(
        self,
        incidents=None,
    ):
        self.incidents = (
            incidents
            or []
        )

    def get_all(self):

        return list(
            self.incidents
        )


def test_attention_is_healthy_when_no_active_signals():

    service = OperationalAttentionService(
        health_repository=(
            FakeHealthRepository()
        ),
        incident_repository=(
            FakeIncidentRepository()
        ),
        active_event_provider=lambda: [],
    )

    result = service.summary()

    assert (
        result["state"]
        == "HEALTHY"
    )

    assert (
        result["attention_required"]
        is False
    )

    assert (
        result["count"]
        == 0
    )

    assert (
        result["complete"]
        is True
    )


def test_attention_reports_active_event():

    service = OperationalAttentionService(
        health_repository=(
            FakeHealthRepository()
        ),
        incident_repository=(
            FakeIncidentRepository()
        ),
        active_event_provider=lambda: [
            {
                "title":
                    "Synthetic workload unavailable",

                "message":
                    "One workload is not available",

                "asset_id":
                    "application-alpha",

                "severity":
                    "warning",

                "status":
                    "active",
            }
        ],
    )

    result = service.summary()

    assert (
        result["state"]
        == "WARNING"
    )

    assert (
        result["attention_required"]
        is True
    )

    assert (
        result["count"]
        == 1
    )

    assert (
        result["items"][0][
            "kind"
        ]
        == "EVENT"
    )

    assert (
        result["items"][0][
            "asset_id"
        ]
        == "application-alpha"
    )


def test_attention_ignores_resolved_incident():

    service = OperationalAttentionService(
        health_repository=(
            FakeHealthRepository()
        ),
        incident_repository=(
            FakeIncidentRepository(
                [
                    {
                        "id":
                            "INC-TEST",

                        "title":
                            "Resolved synthetic incident",

                        "status":
                            "RESOLVED",

                        "severity":
                            "CRITICAL",
                    }
                ]
            )
        ),
        active_event_provider=lambda: [],
    )

    result = service.summary()

    assert (
        result["state"]
        == "HEALTHY"
    )

    assert (
        result["count"]
        == 0
    )


def test_attention_never_claims_healthy_when_source_failed():

    def broken_events():
        raise RuntimeError(
            "synthetic source failure"
        )

    service = OperationalAttentionService(
        health_repository=(
            FakeHealthRepository()
        ),
        incident_repository=(
            FakeIncidentRepository()
        ),
        active_event_provider=(
            broken_events
        ),
    )

    result = service.summary()

    assert (
        result["state"]
        == "UNKNOWN"
    )

    assert (
        result["complete"]
        is False
    )

    assert (
        result["source_errors"]
    )


def test_attention_does_not_require_legacy_health_source():

    service = OperationalAttentionService(
        health_repository=None,
        incident_repository=(
            FakeIncidentRepository()
        ),
        active_event_provider=lambda: [
            {
                "id":
                    "EVT-1",

                "title":
                    "Synthetic current warning",

                "severity":
                    "WARNING",

                "status":
                    "OPEN",
            }
        ],
    )

    result = service.summary()

    assert (
        result["state"]
        == "WARNING"
    )

    assert (
        result["count"]
        == 1
    )

    assert (
        result["items"][0][
            "kind"
        ]
        == "EVENT"
    )
