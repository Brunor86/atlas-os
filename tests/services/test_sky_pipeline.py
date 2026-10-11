import hashlib
import json

from atlas.services.sky.pipeline import (
    SkyPipelineService,
)


def _capture(
    root,
    observation_id="AUTO-FM116-001",
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

    iq = (
        directory
        / f"{observation_id}.iq"
    )
    iq.write_bytes(
        b"ATLAS-SKY-IQ"
    )

    digest = hashlib.sha256(
        iq.read_bytes()
    ).hexdigest()

    (
        directory
        / f"{observation_id}.iq.sha256"
    ).write_text(
        f"{digest}  {iq}\n"
    )

    (
        directory
        / f"{observation_id}.meta.txt"
    ).write_text(
        "\n".join(
            [
                "start=2026-10-11T20:15:11-03:00",
                "center_hz=138100000",
                "sample_rate=1024000",
                "gain_db=33.8",
            ]
        )
        + "\n"
    )

    return directory


def test_pipeline_creates_pending_manifest(
    tmp_path,
):
    directory = _capture(
        tmp_path
    )

    results = (
        SkyPipelineService(
            tmp_path
        ).scan()
    )

    assert len(results) == 1
    assert (
        results[0]["stage"]
        == "AUDIT_PENDING"
    )
    assert (
        results[0][
            "archive_verified"
        ]
        is True
    )

    manifest = json.loads(
        (
            directory
            / "observation.json"
        ).read_text()
    )

    assert (
        manifest["target"]["name"]
        == "ORBCOMM FM116"
    )
    assert (
        manifest["status"]["archive"]
        == "VERIFIED"
    )
    assert (
        manifest["status"]["rf"]
        == "PENDING"
    )
    assert (
        manifest["pipeline"]["audit_kind"]
        == "orbcomm_digital"
    )


def test_pipeline_merges_audit_and_publishes(
    tmp_path,
):
    directory = _capture(
        tmp_path
    )

    (
        directory
        / "science.png"
    ).write_bytes(
        b"png"
    )

    (
        directory
        / "audit.json"
    ).write_text(
        json.dumps(
            {
                "schema": "atlas-sky-audit/v1",
                "observation_id": (
                    "AUTO-FM116-001"
                ),
                "status": {
                    "rf": "CONFIRMED",
                    "digital": "CONFIRMED",
                    "confidence": "HIGH",
                },
                "results": {
                    "strict_valid_frames": 42,
                    "ephemeris_frames": 3,
                },
                "summary": (
                    "Automatic audit confirmed "
                    "the digital downlink."
                ),
                "artifacts": [
                    "science.png",
                ],
                "audit": {
                    "kind": (
                        "orbcomm_digital"
                    ),
                    "version": "v1",
                },
            }
        )
    )

    result = (
        SkyPipelineService(
            tmp_path
        ).scan()[0]
    )

    assert (
        result["stage"]
        == "PUBLISHED"
    )

    manifest = json.loads(
        (
            directory
            / "observation.json"
        ).read_text()
    )

    assert (
        manifest["status"]["rf"]
        == "CONFIRMED"
    )
    assert (
        manifest["status"]["digital"]
        == "CONFIRMED"
    )
    assert (
        manifest["results"][
            "strict_valid_frames"
        ]
        == 42
    )
    assert (
        "science.png"
        in manifest["artifacts"]
    )


def test_pipeline_preserves_previously_published_manifest(
    tmp_path,
):
    directory = _capture(
        tmp_path,
        observation_id="OUT-ISS-001",
    )

    (
        directory
        / "observation.json"
    ).write_text(
        json.dumps(
            {
                "schema": "atlas-sky-observation/v1",
                "id": "OUT-ISS-001",
                "target": {
                    "name": "International Space Station",
                    "norad_id": 25544,
                    "category": "crewed_station",
                    "purpose": "Test",
                },
                "capture": {
                    "frequency_hz": 437800000,
                    "modulation": "FM",
                },
                "status": {
                    "archive": "VERIFIED",
                    "rf": "CONFIRMED",
                    "confidence": "HIGH_RF",
                },
                "results": {
                    "voice_doppler_correlation": 0.9996,
                },
                "summary": "Already audited.",
                "artifacts": [],
            }
        )
    )

    result = (
        SkyPipelineService(
            tmp_path
        ).scan()[0]
    )

    assert result["stage"] == "PUBLISHED"

    manifest = json.loads(
        (
            directory
            / "observation.json"
        ).read_text()
    )

    assert (
        manifest["status"]["rf"]
        == "CONFIRMED"
    )
