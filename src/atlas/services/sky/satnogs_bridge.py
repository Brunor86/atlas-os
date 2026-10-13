from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil

from datetime import datetime
from pathlib import Path
from typing import Any


class SatnogsBridgeError(RuntimeError):
    pass


class SatnogsBridgeService:
    """
    Import a verified SatNOGS observation into the
    canonical ATLAS Sky observation archive.

    v0.1 intentionally supports the certified
    ORBCOMM FM116 audio-decoder product only.
    """

    def __init__(
        self,
        destination_root: Path | str,
    ):
        self.destination_root = Path(
            destination_root
        )

    def ingest(
        self,
        source_directory: Path | str,
    ) -> dict[str, Any]:
        source = Path(source_directory)

        meta = self._read_meta(
            source / "observation.meta.txt"
        )

        observation_id = meta.get(
            "observation_id"
        )

        if not observation_id:
            raise SatnogsBridgeError(
                "SatNOGS observation_id missing"
            )

        if meta.get("target") != "ORBCOMM FM116":
            raise SatnogsBridgeError(
                "v0.1 only supports ORBCOMM FM116"
            )

        if meta.get("norad_id") != "41189":
            raise SatnogsBridgeError(
                "unexpected NORAD identity"
            )

        decode = source / "decode-v01"

        summary_path = (
            decode / "summary.json"
        )

        chunks_path = (
            decode / "chunks.csv"
        )

        provenance_path = (
            decode / "provenance.json"
        )

        checksums_path = (
            decode / "SHA256SUMS"
        )

        for path in (
            summary_path,
            chunks_path,
            provenance_path,
            checksums_path,
        ):
            if not path.is_file():
                raise SatnogsBridgeError(
                    f"missing product: {path.name}"
                )

        self._verify_checksum_manifest(
            decode,
            checksums_path,
        )

        summary = self._read_json(
            summary_path
        )

        provenance = self._read_json(
            provenance_path
        )

        if (
            str(
                provenance.get(
                    "observation_id"
                )
            )
            != observation_id
        ):
            raise SatnogsBridgeError(
                "provenance observation mismatch"
            )

        audio_candidates = sorted(
            source.glob("*.ogg")
        )

        if len(audio_candidates) != 1:
            raise SatnogsBridgeError(
                "expected exactly one OGG audio product"
            )

        audio = audio_candidates[0]

        audio_sha256 = self._sha256(
            audio
        )

        expected_summary_sha = (
            summary.get(
                "input_sha256"
            )
        )

        expected_provenance_sha = (
            provenance.get(
                "input_sha256"
            )
        )

        if not (
            audio_sha256
            == expected_summary_sha
            == expected_provenance_sha
        ):
            raise SatnogsBridgeError(
                "audio SHA256 provenance mismatch"
            )

        privacy = summary.get(
            "privacy",
            {}
        )

        if (
            privacy.get(
                "message_payloads_exported"
            )
            is not False
        ):
            raise SatnogsBridgeError(
                "privacy contract not satisfied"
            )

        valid_packets = int(
            summary.get(
                "valid_packets_total",
                0,
            )
        )

        accepted_chunks = int(
            summary.get(
                "accepted_chunks",
                0,
            )
        )

        if valid_packets <= 0:
            raise SatnogsBridgeError(
                "no checksum-valid packets"
            )

        packet_counts = summary.get(
            "packet_counts",
            {}
        )

        if not isinstance(
            packet_counts,
            dict,
        ):
            raise SatnogsBridgeError(
                "invalid packet counts"
            )

        aos = meta.get(
            "aos_utc"
        )

        if not aos:
            raise SatnogsBridgeError(
                "AOS timestamp missing"
            )

        try:
            aos_dt = datetime.fromisoformat(
                aos.replace(
                    "Z",
                    "+00:00",
                )
            )
        except ValueError as exc:
            raise SatnogsBridgeError(
                "invalid AOS timestamp"
            ) from exc

        target_id = (
            f"SATNOGS-{observation_id}-FM116"
        )

        destination = (
            self.destination_root
            / f"{aos_dt.year:04d}"
            / f"{aos_dt.month:02d}"
            / f"{aos_dt.day:02d}"
            / target_id
        )

        if destination.exists():
            existing = self._read_json(
                destination
                / "observation.json"
            )

            existing_sha = (
                existing
                .get(
                    "results",
                    {},
                )
                .get(
                    "input_sha256"
                )
            )

            if existing_sha == audio_sha256:
                return {
                    "id": target_id,
                    "state": (
                        "ALREADY_INGESTED"
                    ),
                    "destination": str(
                        destination
                    ),
                }

            raise SatnogsBridgeError(
                "destination already exists "
                "with different evidence"
            )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = (
            destination.parent
            / f".{target_id}.tmp"
        )

        if temporary.exists():
            shutil.rmtree(
                temporary
            )

        temporary.mkdir()

        audio_name = audio.name

        self._copy_or_link(
            audio,
            temporary / audio_name,
        )

        shutil.copy2(
            summary_path,
            temporary
            / "orbcomm_summary.json",
        )

        shutil.copy2(
            chunks_path,
            temporary
            / "orbcomm_chunks.csv",
        )

        shutil.copy2(
            provenance_path,
            temporary
            / "orbcomm_provenance.json",
        )

        artifacts = [
            audio_name,
            "orbcomm_summary.json",
            "orbcomm_chunks.csv",
            "orbcomm_provenance.json",
            "audit.json",
        ]

        results = {
            "strict_valid_frames":
                valid_packets,
            "accepted_windows":
                accepted_chunks,
            "packet_counts":
                packet_counts,
            "input_sha256":
                audio_sha256,
            "audio_duration_s":
                summary.get(
                    "audio_duration_s"
                ),
            "audio_sample_rate_hz":
                summary.get(
                    "sample_rate_hz"
                ),
            "symbol_rate_baud":
                summary.get(
                    "symbol_rate_baud"
                ),
            "samples_per_symbol":
                summary.get(
                    "samples_per_symbol"
                ),
            "satnogs_station_id":
                int(
                    meta.get(
                        "station_id",
                        0,
                    )
                ),
            "satnogs_observation_id":
                int(
                    observation_id
                ),
        }

        status = {
            "archive": "VERIFIED",
            "rf": "CONFIRMED",
            "digital": "CONFIRMED",
            "confidence": "HIGH",
        }

        summary_text = (
            "ATLAS Sky imported SatNOGS "
            f"observation {observation_id} "
            "of ORBCOMM FM116 and "
            f"validated {valid_packets} "
            "checksum-valid digital packets."
        )

        audit = {
            "schema":
                "atlas-sky-audit/v1",
            "observation_id":
                target_id,
            "status": status,
            "results": results,
            "summary": summary_text,
            "artifacts": artifacts,
            "audit": {
                "kind":
                    "orbcomm_digital",
                "version":
                    "satnogs-bridge-v0.1",
                "processor":
                    "orbcomm_audio_decode.py",
            },
        }

        self._write_json(
            temporary / "audit.json",
            audit,
        )

        manifest = {
            "schema":
                "atlas-sky-observation/v1",
            "id":
                target_id,
            "target": {
                "name":
                    "ORBCOMM FM116",
                "norad_id":
                    41189,
                "category":
                    "Comunicaciones comerciales",
                "purpose": (
                    "Recepción y análisis "
                    "de la bajada digital "
                    "ORBCOMM."
                ),
            },
            "source": {
                "type":
                    "SatNOGS",
                "station_id":
                    int(
                        meta.get(
                            "station_id",
                            0,
                        )
                    ),
                "station_name":
                    meta.get(
                        "station_name"
                    ),
                "observation_id":
                    int(
                        observation_id
                    ),
            },
            "capture": {
                "frequency_hz":
                    int(
                        meta.get(
                            "frequency_hz",
                            137800000,
                        )
                    ),
                "modulation":
                    "SDPSK 4800",
                "location":
                    "San Juan, Argentina",
                "aos_utc":
                    aos,
                "los_utc":
                    meta.get(
                        "los_utc"
                    ),
                "max_elevation_deg":
                    float(
                        meta.get(
                            "max_elevation_deg",
                            0,
                        )
                    ),
                "source_product":
                    "SatNOGS FM-demodulated OGG",
            },
            "status":
                status,
            "results":
                results,
            "summary":
                summary_text,
            "artifacts":
                artifacts,
            "pipeline": {
                "stage":
                    "PUBLISHED",
                "archive_verified":
                    True,
                "audit_kind":
                    "orbcomm_digital",
                "audit": audit[
                    "audit"
                ],
            },
        }

        self._write_json(
            temporary
            / "observation.json",
            manifest,
        )

        canonical_meta = "\n".join(
            [
                f"start={aos}",
                "source=satnogs",
                (
                    "station_id="
                    f"{meta.get('station_id')}"
                ),
                (
                    "satnogs_observation_id="
                    f"{observation_id}"
                ),
                (
                    "center_hz="
                    f"{meta.get('frequency_hz')}"
                ),
                (
                    "archive_status="
                    "VERIFIED"
                ),
            ]
        ) + "\n"

        (
            temporary
            / f"{target_id}.meta.txt"
        ).write_text(
            canonical_meta,
            encoding="utf-8",
        )

        os.replace(
            temporary,
            destination,
        )

        return {
            "id": target_id,
            "state": "INGESTED",
            "destination": str(
                destination
            ),
            "valid_packets":
                valid_packets,
            "accepted_windows":
                accepted_chunks,
        }

    @staticmethod
    def _read_meta(
        path: Path,
    ) -> dict[str, str]:
        if not path.is_file():
            raise SatnogsBridgeError(
                "observation metadata missing"
            )

        result = {}

        for line in path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines():
            if "=" not in line:
                continue

            key, value = line.split(
                "=",
                1,
            )

            result[
                key.strip()
            ] = value.strip()

        return result

    @staticmethod
    def _read_json(
        path: Path,
    ) -> dict[str, Any]:
        try:
            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise SatnogsBridgeError(
                f"invalid JSON: {path}"
            ) from exc

        if not isinstance(
            data,
            dict,
        ):
            raise SatnogsBridgeError(
                f"JSON object expected: {path}"
            )

        return data

    @staticmethod
    def _sha256(
        path: Path,
    ) -> str:
        digest = hashlib.sha256()

        with path.open("rb") as handle:
            for block in iter(
                lambda: handle.read(
                    1024 * 1024
                ),
                b"",
            ):
                digest.update(
                    block
                )

        return digest.hexdigest()

    def _verify_checksum_manifest(
        self,
        directory: Path,
        manifest: Path,
    ) -> None:
        checked = 0

        for line in manifest.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines():
            line = line.strip()

            if not line:
                continue

            parts = line.split(
                None,
                1,
            )

            if len(parts) != 2:
                raise SatnogsBridgeError(
                    "invalid SHA256SUMS line"
                )

            expected, name = parts

            name = name.lstrip("*")

            candidate = (
                directory / name
            )

            if (
                candidate.parent
                != directory
                or not candidate.is_file()
            ):
                raise SatnogsBridgeError(
                    "unsafe checksum entry"
                )

            if (
                self._sha256(
                    candidate
                )
                != expected
            ):
                raise SatnogsBridgeError(
                    f"checksum failed: {name}"
                )

            checked += 1

        if checked < 3:
            raise SatnogsBridgeError(
                "incomplete checksum manifest"
            )

    @staticmethod
    def _copy_or_link(
        source: Path,
        destination: Path,
    ) -> None:
        try:
            os.link(
                source,
                destination,
            )
        except OSError:
            shutil.copy2(
                source,
                destination,
            )

    @staticmethod
    def _write_json(
        path: Path,
        data: dict[str, Any],
    ) -> None:
        path.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "source",
        type=Path,
    )

    parser.add_argument(
        "--destination-root",
        type=Path,
        required=True,
    )

    args = parser.parse_args()

    result = SatnogsBridgeService(
        args.destination_root
    ).ingest(
        args.source
    )

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
