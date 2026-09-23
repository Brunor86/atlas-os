from atlas.storage.incident_repository import (
    IncidentRepository,
)


def test_incident_tuple_normalizes_to_record():

    row = (
        "INC-TEST",
        "synthetic_incident",
        "asset-alpha",
        "HIGH",
        "OPEN",
        "[]",
        "[]",
        "[]",
        "{}",
        "synthetic root cause",
        "synthetic diagnosis",
        "[]",
        "[]",
        "2026-01-01T00:00:00",
        "2026-01-01T01:00:00",
    )

    record = (
        IncidentRepository
        ._record(
            row
        )
    )

    assert (
        record["id"]
        == "INC-TEST"
    )

    assert (
        record["asset_id"]
        == "asset-alpha"
    )

    assert (
        record["severity"]
        == "HIGH"
    )

    assert (
        record["status"]
        == "OPEN"
    )

    assert (
        record["diagnosis"]
        == "synthetic diagnosis"
    )
