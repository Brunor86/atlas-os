from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from atlas.services.sky.pipeline import (
    SkyPipelineService,
)


class SkyProcessorService:
    """
    Incremental scientific processor for archived
    ATLAS Sky observations.

    v0.1 supports METEOR LRPT. Other observation
    profiles remain untouched until their dedicated
    auditors are implemented.
    """

    SUPPORTED_AUDIT_KINDS = {
        "meteor_lrpt",
    }

    def __init__(
        self,
        root: Path | str,
        *,
        satdump_command: str = "satdump",
        retry_failed: bool = False,
    ):
        self.root = Path(root)
        self.satdump_command = satdump_command
        self.retry_failed = retry_failed

        self.pipeline = SkyPipelineService(
            self.root
        )

    def scan(
        self,
    ) -> list[dict[str, Any]]:
        results = []

        if not self.root.exists():
            return results

        seen = set()

        for checksum in sorted(
            self.root.rglob("*.iq.sha256")
        ):
            directory = checksum.parent

            if directory in seen:
                continue

            seen.add(directory)

            observation_id = (
                directory.name
            )

            meta = self._read_meta(
                directory,
                observation_id,
            )

            profile = (
                SkyPipelineService
                ._match_profile(
                    observation_id,
                    meta,
                )
            )

            if not profile:
                continue

            if (
                profile.get("audit_kind")
                not in self.SUPPORTED_AUDIT_KINDS
            ):
                continue

            results.append(
                self.process_directory(
                    directory,
                    profile=profile,
                )
            )

        return results

    def process_directory(
        self,
        directory: Path,
        *,
        profile: dict[str, Any]
        | None = None,
    ) -> dict[str, Any]:
        directory = Path(directory)
        observation_id = directory.name

        audit_path = (
            directory
            / "audit.json"
        )

        if audit_path.exists():
            return {
                "id": observation_id,
                "state": "ALREADY_AUDITED",
            }

        state_path = (
            directory
            / "processing.json"
        )

        state = self._load_json(
            state_path
        )

        if (
            state
            and state.get("status") == "FAILED"
            and not self.retry_failed
        ):
            return {
                "id": observation_id,
                "state": (
                    "FAILED_REQUIRES_RETRY"
                ),
            }

        meta = self._read_meta(
            directory,
            observation_id,
        )

        profile = (
            profile
            or SkyPipelineService
            ._match_profile(
                observation_id,
                meta,
            )
        )

        if not profile:
            return {
                "id": observation_id,
                "state": "PROFILE_UNKNOWN",
            }

        audit_kind = profile.get(
            "audit_kind"
        )

        if (
            audit_kind
            not in self.SUPPORTED_AUDIT_KINDS
        ):
            return {
                "id": observation_id,
                "state": "UNSUPPORTED",
                "audit_kind": audit_kind,
            }

        pipeline_result = (
            self.pipeline
            .process_directory(
                directory
            )
        )

        if not pipeline_result[
            "archive_verified"
        ]:
            return {
                "id": observation_id,
                "state": "ARCHIVE_UNVERIFIED",
            }

        if audit_kind == "meteor_lrpt":
            return self._process_meteor(
                directory,
                observation_id,
                state_path,
            )

        return {
            "id": observation_id,
            "state": "UNSUPPORTED",
        }

    def _process_meteor(
        self,
        directory: Path,
        observation_id: str,
        state_path: Path,
    ) -> dict[str, Any]:
        manifest = self._load_json(
            directory / "observation.json"
        )

        if not manifest:
            return {
                "id": observation_id,
                "state": "MANIFEST_MISSING",
            }

        capture = manifest.get(
            "capture",
            {},
        )

        sample_rate = capture.get(
            "sample_rate"
        )

        center_hz = capture.get(
            "center_hz"
        )

        target_hz = capture.get(
            "frequency_hz"
        )

        if not all(
            isinstance(value, int)
            for value in (
                sample_rate,
                center_hz,
                target_hz,
            )
        ):
            return {
                "id": observation_id,
                "state": (
                    "CAPTURE_METADATA_INVALID"
                ),
            }

        iq = (
            directory
            / f"{observation_id}.iq"
        )

        if not iq.exists():
            candidates = sorted(
                directory.glob("*.iq")
            )

            if len(candidates) == 1:
                iq = candidates[0]

        if not iq.exists():
            return {
                "id": observation_id,
                "state": "IQ_MISSING",
            }

        satdump = self._resolve_command()

        if not satdump:
            return {
                "id": observation_id,
                "state": (
                    "PROCESSOR_UNAVAILABLE"
                ),
                "processor": "satdump",
            }

        output_dir = (
            directory
            / "satdump"
        )

        if output_dir.exists():
            shutil.rmtree(output_dir)

        output_dir.mkdir(
            parents=True
        )

        log_path = (
            directory
            / "satdump.log"
        )

        frequency_shift = (
            center_hz
            - target_hz
        )

        command = [
            satdump,
            "pipeline",
            "meteor_m2-x_lrpt",
            "baseband",
            str(iq),
            str(output_dir),
            "--samplerate",
            str(sample_rate),
            "--baseband_format",
            "cu8",
            "--freq_shift",
            str(frequency_shift),
            "--satellite_number",
            "M2-4",
        ]

        self._write_json(
            state_path,
            {
                "schema": (
                    "atlas-sky-processing/v1"
                ),
                "observation_id": observation_id,
                "status": "PROCESSING",
                "processor": "satdump",
                "audit_kind": "meteor_lrpt",
                "command": command,
            },
        )

        return_code = self._execute(
            command,
            log_path,
        )

        if return_code != 0:
            self._write_json(
                state_path,
                {
                    "schema": (
                        "atlas-sky-processing/v1"
                    ),
                    "observation_id": (
                        observation_id
                    ),
                    "status": "FAILED",
                    "processor": "satdump",
                    "audit_kind": (
                        "meteor_lrpt"
                    ),
                    "exit_code": return_code,
                    "log": log_path.name,
                    "command": command,
                },
            )

            return {
                "id": observation_id,
                "state": "FAILED",
                "exit_code": return_code,
            }

        images = sorted(
            path
            for path in output_dir.rglob("*")
            if (
                path.is_file()
                and path.suffix.lower()
                in {
                    ".png",
                    ".jpg",
                    ".jpeg",
                }
            )
        )

        cadus = sorted(
            output_dir.rglob("*.cadu")
        )

        image_count = len(images)

        if image_count:
            rf_status = "CONFIRMED"
            digital_status = "CONFIRMED"
            confidence = "HIGH"

            summary = (
                "ATLAS Sky automatically "
                "processed the METEOR LRPT "
                "capture with SatDump and "
                f"produced {image_count} "
                "image product(s)."
            )
        else:
            rf_status = "INCONCLUSIVE"
            digital_status = (
                "NOT_CONFIRMED"
            )
            confidence = "LOW"

            summary = (
                "SatDump completed the "
                "METEOR LRPT processing "
                "pipeline, but no image "
                "product was recovered."
            )

        artifacts = [
            str(
                path.relative_to(directory)
            )
            for path in images
        ]

        artifacts.extend(
            str(
                path.relative_to(directory)
            )
            for path in cadus
        )

        artifacts.append(
            log_path.name
        )

        audit = {
            "schema": "atlas-sky-audit/v1",
            "observation_id": observation_id,
            "status": {
                "rf": rf_status,
                "digital": digital_status,
                "confidence": confidence,
            },
            "results": {
                "processor": "SatDump",
                "pipeline": (
                    "meteor_m2-x_lrpt"
                ),
                "sample_rate": sample_rate,
                "baseband_format": "cu8",
                "frequency_shift_hz": (
                    frequency_shift
                ),
                "image_count": image_count,
                "cadu_count": len(cadus),
            },
            "summary": summary,
            "artifacts": sorted(
                set(artifacts)
            ),
            "audit": {
                "kind": "meteor_lrpt",
                "version": "v1",
                "processor": "SatDump",
            },
        }

        self._write_json(
            directory / "audit.json",
            audit,
        )

        published = (
            self.pipeline
            .process_directory(
                directory
            )
        )

        self._write_json(
            state_path,
            {
                "schema": (
                    "atlas-sky-processing/v1"
                ),
                "observation_id": observation_id,
                "status": "COMPLETE",
                "processor": "satdump",
                "audit_kind": "meteor_lrpt",
                "pipeline_stage": (
                    published["stage"]
                ),
                "image_count": image_count,
                "cadu_count": len(cadus),
            },
        )

        return {
            "id": observation_id,
            "state": "COMPLETE",
            "stage": published["stage"],
            "images": image_count,
            "cadus": len(cadus),
        }

    def _resolve_command(
        self,
    ) -> str | None:
        if "/" in self.satdump_command:
            path = Path(
                self.satdump_command
            )

            if (
                path.exists()
                and path.is_file()
            ):
                return str(path)

            return None

        return shutil.which(
            self.satdump_command
        )

    @staticmethod
    def _execute(
        command: list[str],
        log_path: Path,
    ) -> int:
        with log_path.open(
            "w",
            encoding="utf-8",
        ) as log:
            result = subprocess.run(
                command,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )

        return result.returncode

    @staticmethod
    def _read_meta(
        directory: Path,
        observation_id: str,
    ) -> dict[str, str]:
        path = (
            directory
            / f"{observation_id}.meta.txt"
        )

        if not path.exists():
            candidates = sorted(
                directory.glob(
                    "*.meta.txt"
                )
            )

            if len(candidates) == 1:
                path = candidates[0]

        return (
            SkyPipelineService
            ._read_meta(path)
        )

    @staticmethod
    def _load_json(
        path: Path,
    ) -> dict[str, Any] | None:
        return (
            SkyPipelineService
            ._load_json(path)
        )

    @staticmethod
    def _write_json(
        path: Path,
        data: dict[str, Any],
    ) -> None:
        temporary = path.with_name(
            path.name + ".tmp"
        )

        temporary.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        temporary.replace(path)
