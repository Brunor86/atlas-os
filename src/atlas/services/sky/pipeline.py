import hashlib
import json
from pathlib import Path
from typing import Any

from atlas.services.sky.profiles import TARGET_PROFILES


class SkyPipelineService:
    """
    Small filesystem-native observation pipeline.

    It deliberately avoids a new database. The archive directory is the
    source of truth:
      capture products -> audit.json -> observation.json -> ATLAS Sky.

    A target-specific auditor may write audit.json later; the pipeline then
    merges it into observation.json without changing the raw observation.
    """

    def __init__(
        self,
        root: Path | str,
    ):
        self.root = Path(root)

    def scan(
        self,
    ) -> list[dict[str, Any]]:
        results = []

        if not self.root.exists():
            return results

        for directory in sorted(
            self._observation_directories()
        ):
            results.append(
                self.process_directory(
                    directory
                )
            )

        return results

    def process_directory(
        self,
        directory: Path,
    ) -> dict[str, Any]:
        observation_id = directory.name

        meta = self._read_meta(
            directory
            / f"{observation_id}.meta.txt"
        )

        profile = self._match_profile(
            observation_id,
            meta,
        )

        manifest_path = (
            directory
            / "observation.json"
        )

        manifest = (
            self._load_json(
                manifest_path
            )
            or self._base_manifest(
                observation_id,
                directory,
                meta,
                profile,
            )
        )

        archive_verified = (
            self._verify_archive(
                directory,
                observation_id,
            )
        )

        manifest.setdefault(
            "pipeline",
            {}
        )

        manifest["pipeline"][
            "archive_verified"
        ] = archive_verified

        if archive_verified:
            manifest.setdefault(
                "status",
                {}
            )["archive"] = "VERIFIED"

        audit_path = (
            directory
            / "audit.json"
        )

        audit = self._load_json(
            audit_path
        )

        if audit:
            manifest = self._merge_audit(
                manifest,
                audit,
            )
            stage = "PUBLISHED"
        else:
            stage = "AUDIT_PENDING"

            manifest.setdefault(
                "status",
                {}
            ).setdefault(
                "rf",
                "PENDING",
            )

            manifest["status"].setdefault(
                "confidence",
                "PENDING",
            )

        manifest["pipeline"][
            "stage"
        ] = stage

        manifest["pipeline"][
            "audit_kind"
        ] = (
            profile.get("audit_kind")
            if profile
            else "unknown"
        )

        manifest_path.write_text(
            json.dumps(
                manifest,
                indent=2,
                ensure_ascii=False,
            ) + "\n",
            encoding="utf-8",
        )

        return {
            "id": observation_id,
            "stage": stage,
            "profile": (
                profile.get("key")
                if profile
                else None
            ),
            "archive_verified": (
                archive_verified
            ),
            "manifest": str(
                manifest_path
            ),
            "audit_present": bool(
                audit
            ),
        }

    def _observation_directories(
        self,
    ):
        seen = set()

        for pattern in (
            "*.iq",
            "*.meta.txt",
            "observation.json",
        ):
            for path in self.root.rglob(
                pattern
            ):
                directory = path.parent

                if directory in seen:
                    continue

                seen.add(directory)
                yield directory

    @staticmethod
    def _read_meta(
        path: Path,
    ) -> dict[str, str]:
        result = {}

        if not path.exists():
            return result

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
    def _load_json(
        path: Path,
    ) -> dict[str, Any] | None:
        if not path.exists():
            return None

        try:
            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ):
            return None

        if not isinstance(
            data,
            dict,
        ):
            return None

        return data

    @staticmethod
    def _match_profile(
        observation_id: str,
        meta: dict[str, str],
    ) -> dict[str, Any] | None:
        upper = observation_id.upper()

        names = {
            "FM116": "fm116",
            "ISS": "iss",
            "METEOR": "meteor_m24",
            "RS44": "rs44",
            "RS-44": "rs44",
            "AO73": "ao73",
            "AO-73": "ao73",
        }

        for token, key in names.items():
            if token in upper:
                return next(
                    (
                        profile
                        for profile in TARGET_PROFILES
                        if profile["key"] == key
                    ),
                    None,
                )

        center = meta.get(
            "center_hz"
        )

        if center:
            try:
                center_mhz = (
                    float(center)
                    / 1_000_000.0
                )
            except ValueError:
                center_mhz = None

            if center_mhz is not None:
                candidates = sorted(
                    TARGET_PROFILES,
                    key=lambda profile: abs(
                        profile[
                            "primary_frequency_mhz"
                        ]
                        - center_mhz
                    ),
                )

                if (
                    candidates
                    and abs(
                        candidates[0][
                            "primary_frequency_mhz"
                        ]
                        - center_mhz
                    ) <= 0.5
                ):
                    return candidates[0]

        return None

    @staticmethod
    def _base_manifest(
        observation_id: str,
        directory: Path,
        meta: dict[str, str],
        profile: dict[str, Any] | None,
    ) -> dict[str, Any]:
        profile = profile or {
            "name": observation_id,
            "norad_id": None,
            "category": "Unknown spacecraft",
            "purpose": (
                "Captured by ATLAS Sky; target "
                "profile not yet identified."
            ),
            "primary_frequency_mhz": (
                float(
                    meta.get(
                        "center_hz",
                        0,
                    )
                )
                / 1_000_000.0
            ),
            "mode": "Unknown",
        }

        artifacts = []

        for path in directory.iterdir():
            if not path.is_file():
                continue

            if path.name in {
                "observation.json",
                "audit.json",
            }:
                continue

            if path.suffix.lower() == ".iq":
                continue

            artifacts.append(
                path.name
            )

        frequency_hz = int(
            round(
                float(
                    profile.get(
                        "primary_frequency_mhz",
                        0,
                    )
                )
                * 1_000_000.0
            )
        )

        manifest = {
            "schema": "atlas-sky-observation/v1",
            "id": observation_id,
            "target": {
                "name": profile.get(
                    "name"
                ),
                "norad_id": profile.get(
                    "norad_id"
                ),
                "category": profile.get(
                    "category"
                ),
                "purpose": profile.get(
                    "purpose"
                ),
            },
            "capture": {
                "frequency_hz": frequency_hz,
                "center_hz": (
                    int(
                        float(
                            meta["center_hz"]
                        )
                    )
                    if meta.get(
                        "center_hz"
                    )
                    else None
                ),
                "sample_rate": (
                    int(
                        float(
                            meta["sample_rate"]
                        )
                    )
                    if meta.get(
                        "sample_rate"
                    )
                    else None
                ),
                "gain_db": (
                    float(
                        meta["gain_db"]
                    )
                    if meta.get(
                        "gain_db"
                    )
                    else None
                ),
                "modulation": profile.get(
                    "mode",
                    "Unknown",
                ),
                "location": (
                    "San Juan, Argentina"
                ),
            },
            "status": {
                "archive": "PRESENT",
                "rf": "PENDING",
                "confidence": "PENDING",
            },
            "results": {},
            "summary": (
                "Observation captured and archived. "
                "Scientific audit is pending."
            ),
            "artifacts": sorted(
                artifacts
            ),
        }

        return manifest

    @staticmethod
    def _verify_archive(
        directory: Path,
        observation_id: str,
    ) -> bool:
        iq = (
            directory
            / f"{observation_id}.iq"
        )

        checksum_file = (
            directory
            / f"{observation_id}.iq.sha256"
        )

        if (
            not iq.exists()
            or not checksum_file.exists()
        ):
            return False

        line = checksum_file.read_text(
            encoding="utf-8",
            errors="replace",
        ).strip()

        if not line:
            return False

        expected = line.split()[0]

        digest = hashlib.sha256()

        with iq.open("rb") as handle:
            while True:
                block = handle.read(
                    8 * 1024 * 1024
                )

                if not block:
                    break

                digest.update(block)

        return (
            digest.hexdigest()
            == expected
        )

    @staticmethod
    def _merge_audit(
        manifest: dict[str, Any],
        audit: dict[str, Any],
    ) -> dict[str, Any]:
        status = audit.get(
            "status"
        )

        if isinstance(
            status,
            dict,
        ):
            manifest.setdefault(
                "status",
                {}
            ).update(
                status
            )

        results = audit.get(
            "results"
        )

        if isinstance(
            results,
            dict,
        ):
            manifest.setdefault(
                "results",
                {}
            ).update(
                results
            )

        summary = audit.get(
            "summary"
        )

        if summary:
            manifest[
                "summary"
            ] = str(summary)

        audit_artifacts = audit.get(
            "artifacts",
            []
        )

        if isinstance(
            audit_artifacts,
            list,
        ):
            manifest[
                "artifacts"
            ] = sorted(
                set(
                    manifest.get(
                        "artifacts",
                        []
                    )
                )
                | {
                    str(item)
                    for item in audit_artifacts
                }
            )

        manifest.setdefault(
            "pipeline",
            {}
        )["audit"] = audit.get(
            "audit",
            {}
        )

        return manifest
