import hashlib
import json
from pathlib import Path

from atlas.services.sky.processor import (
    SkyProcessorService,
)


def _meteor_capture(
    root: Path,
):
    observation_id = (
        "OUT-METEOR-M24-TEST"
    )

    directory = (
        root
        / "2026"
        / "10"
        / "12"
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
        b"ATLAS-METEOR-IQ"
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
                (
                    "start="
                    "2026-10-12T03:27:32-03:00"
                ),
                "center_hz=138100000",
                "sample_rate=1024000",
                "gain_db=33.8",
                "archive_status=VERIFIED",
            ]
        )
        + "\n"
    )

    return directory


def test_meteor_processor_publishes_audit(
    tmp_path,
    monkeypatch,
):
    directory = _meteor_capture(
        tmp_path
    )

    service = SkyProcessorService(
        tmp_path,
        satdump_command=(
            "/fake/satdump"
        ),
    )

    monkeypatch.setattr(
        service,
        "_resolve_command",
        lambda: "/fake/satdump",
    )

    calls = []

    def fake_execute(
        command,
        log_path,
    ):
        calls.append(command)

        output = Path(
            command[5]
        )

        output.mkdir(
            parents=True,
            exist_ok=True,
        )

        (
            output
            / "meteor-image.png"
        ).write_bytes(
            b"PNG"
        )

        (
            output
            / "meteor.cadu"
        ).write_bytes(
            b"CADU"
        )

        log_path.write_text(
            "SatDump test\n"
        )

        return 0

    monkeypatch.setattr(
        service,
        "_execute",
        fake_execute,
    )

    result = service.scan()

    assert len(result) == 1
    assert (
        result[0]["state"]
        == "COMPLETE"
    )
    assert (
        result[0]["stage"]
        == "PUBLISHED"
    )
    assert (
        result[0]["images"]
        == 1
    )

    command = calls[0]

    assert (
        "meteor_m2-x_lrpt"
        in command
    )

    assert (
        "--samplerate=1024000"
        in command
    )

    assert (
        "--baseband_format=cu8"
        in command
    )

    assert (
        "--freq_shift=200000"
        in command
    )

    assert (
        "--satellite_number=M2-4"
        in command
    )

    audit = json.loads(
        (
            directory
            / "audit.json"
        ).read_text()
    )

    assert (
        audit["status"]["digital"]
        == "CONFIRMED"
    )

    manifest = json.loads(
        (
            directory
            / "observation.json"
        ).read_text()
    )

    assert (
        manifest["pipeline"]["stage"]
        == "PUBLISHED"
    )


def test_missing_satdump_keeps_pending(
    tmp_path,
    monkeypatch,
):
    directory = _meteor_capture(
        tmp_path
    )

    service = SkyProcessorService(
        tmp_path
    )

    monkeypatch.setattr(
        service,
        "_resolve_command",
        lambda: None,
    )

    result = service.scan()

    assert (
        result[0]["state"]
        == "PROCESSOR_UNAVAILABLE"
    )

    assert not (
        directory
        / "audit.json"
    ).exists()

    manifest = json.loads(
        (
            directory
            / "observation.json"
        ).read_text()
    )

    assert (
        manifest["pipeline"]["stage"]
        == "AUDIT_PENDING"
    )


def test_meteor_processor_waits_for_verified_archive(
    tmp_path,
):
    directory = _meteor_capture(
        tmp_path
    )

    meta = next(
        directory.glob(
            "*.meta.txt"
        )
    )

    text = meta.read_text()

    meta.write_text(
        text.replace(
            "archive_status=VERIFIED",
            "archive_status=PENDING",
        )
    )

    service = SkyProcessorService(
        tmp_path,
        satdump_command=(
            "/fake/satdump"
        ),
    )

    result = service.scan()

    assert len(result) == 1

    assert (
        result[0]["state"]
        == "ARCHIVE_NOT_READY"
    )

    assert (
        result[0]["archive_status"]
        == "PENDING"
    )

    assert not (
        directory
        / "observation.json"
    ).exists()

    assert not (
        directory
        / "processing.json"
    ).exists()

    assert not (
        directory
        / "audit.json"
    ).exists()


def test_processor_does_not_treat_frequency_only_capture_as_meteor(
    tmp_path,
):
    directory = (
        tmp_path
        / "2026"
        / "10"
        / "12"
        / "OUT-BASELINE-138"
    )

    directory.mkdir(
        parents=True
    )

    iq = (
        directory
        / "OUT-BASELINE-138.iq"
    )

    iq.write_bytes(
        b"\x80\x80" * 1024
    )

    import hashlib

    digest = hashlib.sha256(
        iq.read_bytes()
    ).hexdigest()

    (
        directory
        / "OUT-BASELINE-138.iq.sha256"
    ).write_text(
        f"{digest}  {iq}\n"
    )

    (
        directory
        / "OUT-BASELINE-138.meta.txt"
    ).write_text(
        "\n".join(
            [
                "center_hz=138100000",
                "sample_rate=1024000",
                "gain_db=33.8",
                "archive_status=VERIFIED",
            ]
        )
        + "\n"
    )

    service = SkyProcessorService(
        tmp_path,
        satdump_command="/fake/satdump",
    )

    result = service.scan()

    assert result == []

    assert not (
        directory
        / "processing.json"
    ).exists()

    assert not (
        directory
        / "audit.json"
    ).exists()

    assert not (
        directory
        / "observation.json"
    ).exists()
