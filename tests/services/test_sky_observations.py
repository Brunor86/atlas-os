import json
from pathlib import Path

from atlas.services.sky.observations import (
    SkyObservationService,
)


def _write_observation(
    root: Path,
    observation_id: str,
    *,
    rf: str = "CONFIRMED",
):
    directory = (
        root
        / "2026"
        / "10"
        / "11"
        / observation_id
    )

    directory.mkdir(
        parents=True
    )

    manifest = {
        "schema": "atlas-sky-observation/v1",
        "id": observation_id,
        "target": {
            "name": "Test Satellite",
            "norad_id": 12345,
            "category": "test",
            "purpose": "Test mission",
        },
        "capture": {
            "frequency_hz": 137800000,
            "modulation": "TEST",
        },
        "status": {
            "archive": "VERIFIED",
            "rf": rf,
            "digital": "CONFIRMED",
        },
        "results": {
            "strict_valid_frames": 10,
            "ephemeris_frames": 2,
        },
        "artifacts": [
            "plot.png",
            "data.csv",
        ],
    }

    (
        directory
        / "observation.json"
    ).write_text(
        json.dumps(manifest)
    )

    (
        directory
        / f"{observation_id}.meta.txt"
    ).write_text(
        "start=2026-10-11T20:00:00-03:00\n"
    )

    (
        directory
        / "plot.png"
    ).write_bytes(
        b"png"
    )

    (
        directory
        / "data.csv"
    ).write_text(
        "a,b\n1,2\n"
    )

    return directory


def test_discovers_observation_manifests(
    tmp_path,
):
    _write_observation(
        tmp_path,
        "OBS-001",
    )

    service = SkyObservationService(
        tmp_path
    )

    observations = (
        service.list_observations()
    )

    assert len(observations) == 1

    observation = observations[0]

    assert observation["id"] == "OBS-001"
    assert (
        observation["observation_date"]
        == "2026-10-11"
    )
    assert (
        observation["capture_start"]
        == "2026-10-11T20:00:00-03:00"
    )


def test_overview_sums_science_results(
    tmp_path,
):
    _write_observation(
        tmp_path,
        "OBS-001",
    )

    _write_observation(
        tmp_path,
        "OBS-002",
        rf="NOT_CONFIRMED",
    )

    summary = (
        SkyObservationService(
            tmp_path
        ).overview()
    )

    assert summary["observations"] == 2
    assert summary["rf_confirmed"] == 1
    assert summary["digital_confirmed"] == 2
    assert summary["strict_valid_frames"] == 20
    assert summary["ephemeris_frames"] == 4


def test_artifacts_are_manifest_allowlisted(
    tmp_path,
):
    directory = _write_observation(
        tmp_path,
        "OBS-001",
    )

    (
        directory
        / "raw.iq"
    ).write_bytes(
        b"secret"
    )

    service = SkyObservationService(
        tmp_path
    )

    assert (
        service.artifact_path(
            "OBS-001",
            "plot.png",
        )
        == directory / "plot.png"
    )

    assert (
        service.artifact_path(
            "OBS-001",
            "raw.iq",
        )
        is None
    )

    assert (
        service.artifact_path(
            "OBS-001",
            "../plot.png",
        )
        is None
    )
