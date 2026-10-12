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

    assert "cu8" in command

    shift_index = command.index(
        "--freq_shift"
    )

    assert (
        command[
            shift_index + 1
        ]
        == "200000"
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
