import json
import os
from pathlib import Path
from typing import Any


DEFAULT_OBSERVATIONS_ROOT = Path(
    os.getenv(
        "ATLAS_SKY_OBSERVATIONS_ROOT",
        "/mnt/datos12tb/atlas-sky/observations",
    )
)


class SkyObservationService:
    """
    Read-only view over ATLAS Sky observation manifests.

    The observation archive remains the source of truth. This service
    discovers observation.json files and never mutates capture products.
    """

    def __init__(
        self,
        root: Path | str | None = None,
    ):
        self.root = Path(
            root or DEFAULT_OBSERVATIONS_ROOT
        )

    def available(self) -> bool:
        return (
            self.root.exists()
            and self.root.is_dir()
        )

    def list_observations(
        self,
    ) -> list[dict[str, Any]]:
        observations: list[dict[str, Any]] = []

        if not self.available():
            return observations

        for manifest_path in self.root.rglob(
            "observation.json"
        ):
            observation = self._load_manifest(
                manifest_path
            )

            if observation is None:
                continue

            observations.append(
                observation
            )

        observations.sort(
            key=lambda item: (
                item.get("capture_start") or "",
                item.get("id") or "",
            ),
            reverse=True,
        )

        return observations

    def overview(
        self,
    ) -> dict[str, Any]:
        observations = self.list_observations()

        return {
            "available": self.available(),
            "root": str(self.root),
            "observations": len(observations),
            "rf_confirmed": sum(
                1
                for item in observations
                if (
                    item.get("status", {})
                    .get("rf")
                    == "CONFIRMED"
                )
            ),
            "digital_confirmed": sum(
                1
                for item in observations
                if (
                    item.get("status", {})
                    .get("digital")
                    == "CONFIRMED"
                )
            ),
            "strict_valid_frames": sum(
                int(
                    item.get("results", {})
                    .get("strict_valid_frames", 0)
                    or 0
                )
                for item in observations
            ),
            "ephemeris_frames": sum(
                int(
                    item.get("results", {})
                    .get("ephemeris_frames", 0)
                    or 0
                )
                for item in observations
            ),
        }

    def get_observation(
        self,
        observation_id: str,
    ) -> dict[str, Any] | None:
        for observation in self.list_observations():
            if observation.get("id") == observation_id:
                return observation

        return None

    def artifact_path(
        self,
        observation_id: str,
        artifact_name: str,
    ) -> Path | None:
        observation = self.get_observation(
            observation_id
        )

        if observation is None:
            return None

        declared = set(
            observation.get(
                "artifacts",
                [],
            )
        )

        if artifact_name not in declared:
            return None

        name = Path(artifact_name)

        # v1 manifests only expose files directly inside the
        # observation directory. Never serve raw IQ from /sky.
        if (
            name.name != artifact_name
            or name.suffix.lower() == ".iq"
        ):
            return None

        directory = Path(
            observation["_directory"]
        ).resolve()

        candidate = (
            directory
            / artifact_name
        ).resolve()

        if candidate.parent != directory:
            return None

        if (
            not candidate.exists()
            or not candidate.is_file()
        ):
            return None

        return candidate

    def _load_manifest(
        self,
        manifest_path: Path,
    ) -> dict[str, Any] | None:
        try:
            data = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ):
            return None

        observation_id = str(
            data.get("id", "")
        ).strip()

        if not observation_id:
            return None

        item = dict(data)

        item["_manifest"] = str(
            manifest_path
        )
        item["_directory"] = str(
            manifest_path.parent
        )

        item["capture_start"] = (
            self._capture_start(
                manifest_path.parent,
                observation_id,
            )
        )

        item["observation_date"] = (
            self._observation_date(
                manifest_path
            )
        )

        item["artifact_inventory"] = (
            self._artifact_inventory(
                item
            )
        )

        return item

    @staticmethod
    def _capture_start(
        directory: Path,
        observation_id: str,
    ) -> str | None:
        meta = (
            directory
            / f"{observation_id}.meta.txt"
        )

        if not meta.exists():
            return None

        try:
            for line in meta.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines():
                if line.startswith("start="):
                    return line.split(
                        "=",
                        1,
                    )[1].strip()
        except OSError:
            return None

        return None

    def _observation_date(
        self,
        manifest_path: Path,
    ) -> str | None:
        try:
            relative = manifest_path.relative_to(
                self.root
            )
        except ValueError:
            return None

        parts = relative.parts

        if len(parts) < 4:
            return None

        year, month, day = parts[:3]

        if not (
            year.isdigit()
            and month.isdigit()
            and day.isdigit()
        ):
            return None

        return f"{year}-{month}-{day}"

    @staticmethod
    def _artifact_inventory(
        observation: dict[str, Any],
    ) -> list[dict[str, Any]]:
        directory = Path(
            observation["_directory"]
        )

        inventory = []

        for name in observation.get(
            "artifacts",
            [],
        ):
            path = directory / name

            suffix = path.suffix.lower()

            if suffix in {
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
            }:
                kind = "image"
            elif suffix in {
                ".wav",
                ".mp3",
                ".ogg",
            }:
                kind = "audio"
            elif suffix in {
                ".csv",
                ".json",
                ".kml",
                ".md",
                ".txt",
                ".sha256",
            }:
                kind = "data"
            else:
                kind = "file"

            inventory.append(
                {
                    "name": name,
                    "kind": kind,
                    "exists": (
                        path.exists()
                        and path.is_file()
                    ),
                    "size_bytes": (
                        path.stat().st_size
                        if path.exists()
                        and path.is_file()
                        else None
                    ),
                }
            )

        return inventory
