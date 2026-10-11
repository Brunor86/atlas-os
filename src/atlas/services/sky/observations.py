import json
import os
from pathlib import Path
from typing import Any

from atlas.services.sky.discovery import (
    SkyDiscoveryService,
)
from atlas.services.sky.profiles import (
    STATION_CAPABILITIES,
    TARGET_PROFILES,
)


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
        catalog = self.catalog()

        return {
            "available": self.available(),
            "root": str(self.root),
            "observations": len(observations),
            "catalog_targets": len(catalog),
            "current_candidates": sum(
                1
                for item in catalog
                if int(
                    item.get(
                        "reception_score",
                        0,
                    )
                    or 0
                ) >= 60
            ),
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

    def catalog(
        self,
    ) -> list[dict[str, Any]]:
        seeds = [
            {
                **dict(item),
                "catalog_source": "curado",
                "reception_score": 100,
                "reception_level": "VALIDADO",
            }
            for item in TARGET_PROFILES
        ]

        discovered = (
            SkyDiscoveryService()
            .load_cache()
            .get(
                "targets",
                [],
            )
        )

        known_norad = {
            item.get("norad_id")
            for item in seeds
            if item.get("norad_id")
        }

        dynamic = []

        for item in discovered:
            norad = item.get(
                "norad_id"
            )

            if (
                norad
                and norad in known_norad
            ):
                continue

            dynamic.append(
                {
                    "key": (
                        f"satnogs-{item.get('transmitter_uuid')}"
                    ),
                    "name": item.get(
                        "satellite_name",
                        "Objeto sin nombre",
                    ),
                    "norad_id": norad,
                    "category": "Transmisor activo SatNOGS",
                    "primary_frequency_mhz": item.get(
                        "downlink_mhz"
                    ),
                    "mode": item.get(
                        "mode",
                        "Desconocido",
                    ),
                    "purpose": (
                        "Transmisor activo registrado en SatNOGS DB. "
                        "ATLAS Sky todavía no realizó una observación "
                        "confirmada de este objetivo."
                    ),
                    "atlas_can_read": [
                        "Firma Doppler orbital",
                        (
                            "Señal y modulación del transmisor si el "
                            "margen del enlace es suficiente"
                        ),
                        (
                            "Telemetría o contenido adicional cuando "
                            "exista un decodificador compatible"
                        ),
                    ],
                    "audit_kind": "generic_rf",
                    "catalog_source": "SatNOGS DB",
                    "reception_score": item.get(
                        "reception_score",
                        0,
                    ),
                    "reception_level": item.get(
                        "reception_level",
                        "EXPLORATORIO",
                    ),
                    "reception_reason": item.get(
                        "reception_reason"
                    ),
                }
            )

        dynamic.sort(
            key=lambda item: (
                -int(
                    item.get(
                        "reception_score",
                        0,
                    )
                ),
                item.get("name") or "",
            )
        )

        return seeds + dynamic[:100]

    def station_capabilities(
        self,
    ) -> list[dict[str, Any]]:
        return [
            dict(item)
            for item in STATION_CAPABILITIES
        ]

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

        item["display_status"] = (
            self._display_status(
                item.get(
                    "status",
                    {},
                )
            )
        )

        item["display_summary"] = (
            self._display_summary(
                item
            )
        )

        item["display_purpose"] = (
            self._display_purpose(
                item
            )
        )

        item["highlight_results"] = (
            self._highlight_results(
                item
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
    def _display_status(
        status: dict[str, Any],
    ) -> dict[str, str]:
        translations = {
            "VERIFIED": "VERIFICADO",
            "PRESENT": "PRESENTE",
            "CONFIRMED": "CONFIRMADA",
            "NOT_CONFIRMED": "NO CONFIRMADA",
            "INCONCLUSIVE": "INCONCLUSA",
            "PENDING": "PENDIENTE",
            "PROBABLE_NOT_INTELLIGIBLE": "PROBABLE · NO INTELIGIBLE",
            "HIGH": "ALTA",
            "HIGH_RF": "ALTA · RF",
        }

        return {
            key: translations.get(
                str(value),
                str(value).replace(
                    "_",
                    " ",
                ),
            )
            for key, value in status.items()
        }

    @staticmethod
    def _display_summary(
        observation: dict[str, Any],
    ) -> str:
        known = {
            "OUT-FM116-PRE": (
                "ATLAS Sky recibió y decodificó la bajada digital de "
                "ORBCOMM FM116, reconstruyó telemetría orbital transmitida "
                "por la nave y validó la trayectoria contra CelesTrak."
            ),
            "OUT-ISS-001": (
                "ATLAS Sky confirmó la bajada de la ISS en 437.800 MHz "
                "mediante su firma Doppler orbital. Se recuperó un fragmento "
                "compatible con voz, pero sin contenido inteligible; APRS "
                "no quedó confirmado."
            ),
        }

        return known.get(
            observation.get("id"),
            str(
                observation.get(
                    "summary",
                    "Observación archivada por ATLAS Sky.",
                )
            ),
        )

    @staticmethod
    def _display_purpose(
        observation: dict[str, Any],
    ) -> str:
        norad = (
            observation.get(
                "target",
                {},
            ).get(
                "norad_id"
            )
        )

        for profile in TARGET_PROFILES:
            if (
                profile.get(
                    "norad_id"
                )
                == norad
            ):
                return str(
                    profile.get(
                        "purpose",
                        "",
                    )
                )

        return str(
            observation.get(
                "target",
                {},
            ).get(
                "purpose",
                "",
            )
        )

    @staticmethod
    def _highlight_results(
        observation: dict[str, Any],
    ) -> list[dict[str, str]]:
        results = observation.get(
            "results",
            {},
        )

        observation_id = observation.get(
            "id"
        )

        if observation_id == "OUT-FM116-PRE":
            values = [
                (
                    "Efemérides decodificadas",
                    results.get("ephemeris_frames"),
                    "estados orbitales recibidos por radio",
                ),
                (
                    "Tramas válidas estrictas",
                    results.get("strict_valid_frames"),
                    "paquetes crudos con checksum válido",
                ),
                (
                    "Error medio de posición",
                    (
                        f'{results.get("mean_position_error_km"):.3f} km'
                        if results.get("mean_position_error_km") is not None
                        else None
                    ),
                    "efemérides decodificadas vs TLE independiente",
                ),
                (
                    "Error medio de velocidad",
                    (
                        f'{results.get("mean_velocity_error_m_s"):.3f} m/s'
                        if results.get("mean_velocity_error_m_s") is not None
                        else None
                    ),
                    "velocidad decodificada vs órbita de referencia",
                ),
            ]

        elif observation_id == "OUT-ISS-001":
            values = [
                (
                    "Correlación Doppler",
                    (
                        f'{results.get("voice_doppler_correlation"):.4f}'
                        if results.get("voice_doppler_correlation") is not None
                        else None
                    ),
                    "portadora observada vs modelo orbital de la ISS",
                ),
                (
                    "Ventaja orbital",
                    (
                        f'+{results.get("voice_orbital_advantage_db"):.2f} dB'
                        if results.get("voice_orbital_advantage_db") is not None
                        else None
                    ),
                    "modelo orbital frente a controles estacionarios",
                ),
                (
                    "Excursión de frecuencia",
                    (
                        f'{results.get("voice_frequency_span_hz") / 1000:.3f} kHz'
                        if results.get("voice_frequency_span_hz") is not None
                        else None
                    ),
                    "rango Doppler medido durante el pase",
                ),
                (
                    "Elevación máxima",
                    (
                        f'{results.get("predicted_max_elevation_deg"):.2f}°'
                        if results.get("predicted_max_elevation_deg") is not None
                        else None
                    ),
                    "geometría prevista para este pase",
                ),
            ]

        else:
            values = []

        return [
            {
                "label": label,
                "value": str(value),
                "note": note,
            }
            for label, value, note in values
            if value is not None
        ]

    @staticmethod
    def _artifact_inventory(
        observation: dict[str, Any],
    ) -> list[dict[str, Any]]:
        directory = Path(
            observation["_directory"]
        )

        results = observation.get(
            "results",
            {},
        )

        presentations = {
            "trajectory_comparison.png": {
                "title": "Validación de trayectoria orbital",
                "description": (
                    "Decoded FM116 ephemerides compared with the "
                    "independent CelesTrak reference trajectory. "
                    "Near-overlap is the expected result."
                ),
                "metric": (
                    f'Error medio {results.get("mean_position_error_km"):.3f} km'
                    if results.get("mean_position_error_km") is not None
                    else None
                ),
            },
            "ephemeris_position_error.png": {
                "title": "Error de posición vs referencia",
                "description": (
                    "Distance between the position transmitted by "
                    "FM116 and the reference TLE solution over time."
                ),
                "metric": (
                    f'Máx. {results.get("max_position_error_km"):.3f} km'
                    if results.get("max_position_error_km") is not None
                    else None
                ),
            },
            "ephemeris_altitude.png": {
                "title": "Concordancia de altitud",
                "description": (
                    "Altitude decoded directly from the satellite "
                    "compared with the independent orbital model."
                ),
                "metric": (
                    (
                        f'{results.get("altitude_min_km"):.2f}–'
                        f'{results.get("altitude_max_km"):.2f} km'
                    )
                    if (
                        results.get("altitude_min_km") is not None
                        and results.get("altitude_max_km") is not None
                    )
                    else None
                ),
            },
            "OUT-ISS-001_strict_rf.png": {
                "title": "Confirmación Doppler orbital de la ISS",
                "description": (
                    "Received 437.800 MHz carrier tracked against the "
                    "predicted ISS Doppler curve after receiver-frame "
                    "stationary components were controlled."
                ),
                "metric": (
                    (
                        f'corr {results.get("voice_doppler_correlation"):.4f} · '
                        f'+{results.get("voice_orbital_advantage_db"):.2f} dB'
                    )
                    if (
                        results.get("voice_doppler_correlation") is not None
                        and results.get("voice_orbital_advantage_db") is not None
                    )
                    else None
                ),
            },
        }

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

            presentation = presentations.get(
                name,
                {},
            )

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
                    "title": presentation.get(
                        "title",
                        name.replace("_", " "),
                    ),
                    "description": presentation.get(
                        "description"
                    ),
                    "metric": presentation.get(
                        "metric"
                    ),
                }
            )

        return inventory
