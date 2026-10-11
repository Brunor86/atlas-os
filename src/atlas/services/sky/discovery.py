import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


SATNOGS_BASE_URL = "https://db.satnogs.org/api"

DEFAULT_CATALOG_PATH = Path(
    os.getenv(
        "ATLAS_SKY_CATALOG_PATH",
        "/mnt/datos12tb/atlas-sky/catalog/discoverable_targets.json",
    )
)


@dataclass(frozen=True)
class ReceptionBand:
    low_hz: float
    high_hz: float
    score: int
    level: str
    reason: str


# This is a station/antenna model, not the SDR tuner limit.
# Entries outside these bands may still be technically tunable and are
# kept in the catalog, but they receive a low exploratory score.
CURRENT_ANTENNA_BANDS = (
    ReceptionBand(
        136_000_000,
        150_000_000,
        100,
        "MUY FAVORABLE",
        "Banda donde el dipolo actual ya demostró recepción digital fuerte.",
    ),
    ReceptionBand(
        400_000_000,
        470_000_000,
        65,
        "POSIBLE",
        "El receptor funciona; la antena VHF actual está desadaptada en UHF.",
    ),
    ReceptionBand(
        1_080_000_000,
        1_100_000_000,
        25,
        "EXPERIMENTAL",
        "La antena actual está muy desadaptada; conviene una antena ADS-B.",
    ),
)


# Official RTL-SDR Blog V3 hardware coverage. Below ~24 MHz reception
# uses direct sampling and needs a suitable HF antenna/filtering.
RTLSDR_V3_LOW_HZ = 500_000
RTLSDR_V3_HIGH_HZ = 1_766_000_000


class SkyDiscoveryService:
    """
    Build a local, receiver-aware catalog from public SatNOGS DB data.

    Network access is used only by refresh(). The ATLAS Sky web page reads
    the resulting local JSON cache, so opening /sky never depends on an
    external service.
    """

    def __init__(
        self,
        cache_path: Path | str | None = None,
    ):
        self.cache_path = Path(
            cache_path or DEFAULT_CATALOG_PATH
        )

    def load_cache(
        self,
    ) -> dict[str, Any]:
        if not self.cache_path.exists():
            return {
                "generated_at": None,
                "source": "SatNOGS DB",
                "targets": [],
            }

        try:
            payload = json.loads(
                self.cache_path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ):
            return {
                "generated_at": None,
                "source": "SatNOGS DB",
                "targets": [],
            }

        if not isinstance(payload, dict):
            return {
                "generated_at": None,
                "source": "SatNOGS DB",
                "targets": [],
            }

        payload.setdefault(
            "targets",
            [],
        )

        return payload

    def refresh(
        self,
        *,
        max_pages: int = 100,
    ) -> dict[str, Any]:
        satellites = self._collect_endpoint(
            f"{SATNOGS_BASE_URL}/satellites/",
            max_pages=max_pages,
        )

        transmitters = self._collect_endpoint(
            f"{SATNOGS_BASE_URL}/transmitters/",
            max_pages=max_pages,
        )

        satellite_map = self._satellite_map(
            satellites
        )

        targets = []

        for raw in transmitters:
            normalized = self._normalize_transmitter(
                raw,
                satellite_map,
            )

            if normalized is None:
                continue

            targets.append(
                normalized
            )

        targets.sort(
            key=lambda item: (
                -item["reception_score"],
                item.get("satellite_name") or "",
                item.get("downlink_hz") or 0,
            )
        )

        payload = {
            "schema": "atlas-sky-discovery/v1",
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "source": "SatNOGS DB",
            "receiver": "RTL-SDR Blog V3",
            "antenna_profile": "dipolo exterior ~54 cm por brazo",
            "targets": targets,
        }

        self.cache_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.cache_path.write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            ) + "\n",
            encoding="utf-8",
        )

        return payload

    @staticmethod
    def _collect_endpoint(
        first_url: str,
        *,
        max_pages: int,
    ) -> list[dict[str, Any]]:
        url = first_url
        rows: list[dict[str, Any]] = []
        pages = 0

        while url and pages < max_pages:
            req = Request(
                url,
                headers={
                    "User-Agent": "ATLAS-SKY/0.3",
                    "Accept": "application/json",
                },
            )

            with urlopen(
                req,
                timeout=30,
            ) as response:
                payload = json.loads(
                    response.read().decode(
                        "utf-8"
                    )
                )

            if isinstance(payload, list):
                rows.extend(
                    item
                    for item in payload
                    if isinstance(item, dict)
                )
                break

            if not isinstance(payload, dict):
                break

            page_rows = payload.get(
                "results",
                payload.get(
                    "data",
                    [],
                ),
            )

            if isinstance(page_rows, list):
                rows.extend(
                    item
                    for item in page_rows
                    if isinstance(item, dict)
                )

            next_url = payload.get(
                "next"
            )

            if not isinstance(
                next_url,
                str,
            ):
                next_url = None

            url = next_url
            pages += 1

        return rows

    @staticmethod
    def _satellite_map(
        satellites: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        result = {}

        for sat in satellites:
            identifiers = [
                sat.get("sat_id"),
                sat.get("id"),
                sat.get("uuid"),
                sat.get("norad_cat_id"),
                sat.get("norad_id"),
            ]

            for identifier in identifiers:
                if identifier is None:
                    continue

                result[
                    str(identifier)
                ] = sat

        return result

    @classmethod
    def _normalize_transmitter(
        cls,
        raw: dict[str, Any],
        satellites: dict[str, dict[str, Any]],
    ) -> dict[str, Any] | None:
        status = str(
            raw.get(
                "status",
                "",
            )
        ).lower()

        if status not in {
            "active",
            "operational",
            "alive",
        }:
            return None

        if raw.get("unconfirmed") is True:
            return None

        downlink = cls._first_number(
            raw,
            (
                "downlink_low",
                "downlink_high",
                "downlink",
                "frequency",
                "center_frequency",
            ),
        )

        if downlink is None:
            return None

        if not (
            RTLSDR_V3_LOW_HZ
            <= downlink
            <= RTLSDR_V3_HIGH_HZ
        ):
            return None

        satellite_ref = raw.get(
            "satellite"
        )

        satellite = {}

        if isinstance(
            satellite_ref,
            dict,
        ):
            satellite = satellite_ref

        elif satellite_ref is not None:
            satellite = satellites.get(
                str(satellite_ref),
                {},
            )

        if not satellite:
            for key in (
                "satellite_id",
                "sat_id",
                "norad_cat_id",
                "norad_id",
            ):
                value = raw.get(key)

                if value is None:
                    continue

                satellite = satellites.get(
                    str(value),
                    {},
                )

                if satellite:
                    break

        name = (
            satellite.get("name")
            or raw.get("satellite_name")
            or raw.get("name")
            or "Objeto sin nombre"
        )

        norad = cls._first_int(
            satellite,
            (
                "norad_cat_id",
                "norad_id",
                "norad",
            ),
        )

        if norad is None:
            norad = cls._first_int(
                raw,
                (
                    "norad_cat_id",
                    "norad_id",
                    "norad",
                ),
            )

        score, level, reason = (
            cls._reception_score(
                downlink
            )
        )

        mode = raw.get("mode")

        if isinstance(mode, dict):
            mode = (
                mode.get("name")
                or mode.get("mode")
            )

        return {
            "source": "SatNOGS DB",
            "transmitter_uuid": (
                raw.get("uuid")
                or raw.get("id")
            ),
            "satellite_name": str(name),
            "norad_id": norad,
            "downlink_hz": int(
                round(downlink)
            ),
            "downlink_mhz": round(
                downlink / 1_000_000.0,
                6,
            ),
            "mode": str(
                mode or "Desconocido"
            ),
            "baud": raw.get("baud"),
            "description": raw.get(
                "description"
            ),
            "service": raw.get(
                "service"
            ),
            "reception_score": score,
            "reception_level": level,
            "reception_reason": reason,
            "current_antenna_candidate": (
                score >= 60
            ),
        }

    @staticmethod
    def _first_number(
        payload: dict[str, Any],
        keys: tuple[str, ...],
    ) -> float | None:
        for key in keys:
            value = payload.get(key)

            if value is None:
                continue

            try:
                return float(value)
            except (
                TypeError,
                ValueError,
            ):
                continue

        return None

    @staticmethod
    def _first_int(
        payload: dict[str, Any],
        keys: tuple[str, ...],
    ) -> int | None:
        value = SkyDiscoveryService._first_number(
            payload,
            keys,
        )

        if value is None:
            return None

        return int(value)

    @staticmethod
    def _reception_score(
        frequency_hz: float,
    ) -> tuple[int, str, str]:
        for band in CURRENT_ANTENNA_BANDS:
            if (
                band.low_hz
                <= frequency_hz
                <= band.high_hz
            ):
                return (
                    band.score,
                    band.level,
                    band.reason,
                )

        if frequency_hz < 24_000_000:
            return (
                5,
                "REQUIERE OTRA ANTENA",
                (
                    "El V3 puede usar muestreo directo en HF, "
                    "pero el dipolo actual no es adecuado."
                ),
            )

        return (
            10,
            "EXPLORATORIO",
            (
                "La frecuencia entra en el rango del RTL-SDR V3, "
                "pero la antena actual no está caracterizada aquí."
            ),
        )
