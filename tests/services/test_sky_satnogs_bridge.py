import hashlib
import json

import pytest

from atlas.services.sky.satnogs_bridge import (
    SatnogsBridgeError,
    SatnogsBridgeService,
)


def _source(tmp_path):
    source = (
        tmp_path
        / "satnogs"
        / "15191789"
    )

    decode = (
        source
        / "decode-v01"
    )

    decode.mkdir(
        parents=True
    )

    audio = (
        source
        / "satnogs_15191789.ogg"
    )

    audio.write_bytes(
        b"ATLAS-SATNOGS-ORBCOMM"
    )

    digest = hashlib.sha256(
        audio.read_bytes()
    ).hexdigest()

    (
        source
        / "observation.meta.txt"
    ).write_text(
        "\n".join(
            [
                "source=SatNOGS",
                "station_id=5251",
                (
                    "station_name="
                    "ATLAS-SKY-SAN-JUAN"
                ),
                "observation_id=15191789",
                "norad_id=41189",
                "target=ORBCOMM FM116",
                "frequency_hz=137800000",
                (
                    "aos_utc="
                    "2026-10-12T22:15:18Z"
                ),
                (
                    "los_utc="
                    "2026-10-12T22:25:22Z"
                ),
                "max_elevation_deg=87",
            ]
        )
        + "\n"
    )

    summary = {
        "schema":
            "atlas-sky-orbcomm-"
            "audio-decode/v1",
        "input_sha256":
            digest,
        "accepted_chunks":
            38,
        "valid_packets_total":
            12191,
        "packet_counts": {
            "Fill": 10779,
            "Message": 851,
            "Sync": 258,
        },
        "audio_duration_s":
            600.043,
        "sample_rate_hz":
            48000,
        "symbol_rate_baud":
            4800,
        "samples_per_symbol":
            10,
        "privacy": {
            "message_payloads_exported":
                False,
        },
    }

    provenance = {
        "observation_id":
            "15191789",
        "input_sha256":
            digest,
    }

    (
        decode
        / "summary.json"
    ).write_text(
        json.dumps(
            summary
        )
    )

    (
        decode
        / "chunks.csv"
    ).write_text(
        "chunk_index,valid_packets\n"
        "1,100\n"
    )

    (
        decode
        / "provenance.json"
    ).write_text(
        json.dumps(
            provenance
        )
    )

    checksum_lines = []

    for name in (
        "summary.json",
        "chunks.csv",
        "provenance.json",
    ):
        path = decode / name

        checksum_lines.append(
            (
                hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                + f"  {name}"
            )
        )

    (
        decode
        / "SHA256SUMS"
    ).write_text(
        "\n".join(
            checksum_lines
        )
        + "\n"
    )

    return source


def test_ingests_verified_satnogs_observation(
    tmp_path,
):
    source = _source(
        tmp_path
    )

    destination = (
        tmp_path
        / "observations"
    )

    result = (
        SatnogsBridgeService(
            destination
        ).ingest(
            source
        )
    )

    assert (
        result["state"]
        == "INGESTED"
    )

    directory = (
        destination
        / "2026"
        / "10"
        / "12"
        / "SATNOGS-15191789-FM116"
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
        == 12191
    )

    assert (
        manifest["results"][
            "satnogs_station_id"
        ]
        == 5251
    )

    assert (
        manifest["source"][
            "observation_id"
        ]
        == 15191789
    )

    for artifact in manifest[
        "artifacts"
    ]:
        assert (
            directory
            / artifact
        ).is_file()


def test_ingest_is_idempotent(
    tmp_path,
):
    source = _source(
        tmp_path
    )

    destination = (
        tmp_path
        / "observations"
    )

    service = (
        SatnogsBridgeService(
            destination
        )
    )

    first = service.ingest(
        source
    )

    second = service.ingest(
        source
    )

    assert (
        first["state"]
        == "INGESTED"
    )

    assert (
        second["state"]
        == "ALREADY_INGESTED"
    )


def test_rejects_exported_message_payloads(
    tmp_path,
):
    source = _source(
        tmp_path
    )

    summary_path = (
        source
        / "decode-v01"
        / "summary.json"
    )

    summary = json.loads(
        summary_path.read_text()
    )

    summary["privacy"][
        "message_payloads_exported"
    ] = True

    summary_path.write_text(
        json.dumps(
            summary
        )
    )

    decode = (
        source
        / "decode-v01"
    )

    lines = []

    for name in (
        "summary.json",
        "chunks.csv",
        "provenance.json",
    ):
        path = decode / name

        lines.append(
            hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            + f"  {name}"
        )

    (
        decode
        / "SHA256SUMS"
    ).write_text(
        "\n".join(lines)
        + "\n"
    )

    with pytest.raises(
        SatnogsBridgeError,
        match="privacy",
    ):
        SatnogsBridgeService(
            tmp_path
            / "observations"
        ).ingest(
            source
        )
