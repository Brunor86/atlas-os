import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


DEFAULT_CATALOG_PATH = Path(
    os.getenv(
        "ATLAS_SKY_CATALOG_PATH",
        "/mnt/datos12tb/atlas-sky/catalog/discoverable_targets.json",
    )
)

DEFAULT_OPPORTUNITIES_PATH = Path(
    os.getenv(
        "ATLAS_SKY_OPPORTUNITIES_PATH",
        "/mnt/datos12tb/atlas-sky/catalog/opportunities.json",
    )
)

CELESTRAK_ACTIVE_TLE = (
    "https://celestrak.org/NORAD/elements/"
    "gp.php?GROUP=active&FORMAT=tle"
)


def _expected_product(
    mode: str,
    description: str | None,
) -> str:
    text = (
        f"{mode} {description or ''}"
    ).upper()

    if "LRPT" in text or "APT" in text:
        return "Imagen meteorológica"

    if "SSTV" in text:
        return "Imagen SSTV"

    if "APRS" in text or "AX.25" in text or "AFSK" in text:
        return "Paquetes AX.25 / APRS"

    if "GMSK" in text or "BPSK" in text or "FSK" in text:
        return "Telemetría digital"

    if "CW" in text:
        return "Baliza / telemetría CW"

    if "FMN" in text or mode.upper() == "FM":
        return "Audio / voz"

    return "Señal RF + firma Doppler"


def _pass_bonus(
    *,
    max_elevation_deg: float,
    product: str,
) -> int:
    elevation_bonus = int(
        min(
            30,
            max(
                0,
                max_elevation_deg - 10,
            ),
        )
    )

    product_bonus = {
        "Imagen meteorológica": 30,
        "Imagen SSTV": 28,
        "Telemetría digital": 24,
        "Paquetes AX.25 / APRS": 22,
        "Audio / voz": 18,
        "Baliza / telemetría CW": 14,
        "Señal RF + firma Doppler": 8,
    }.get(
        product,
        8,
    )

    return (
        elevation_bonus
        + product_bonus
    )


class SkyOpportunityService:
    """
    Transform the broad radio catalog into a small set of real orbital
    opportunities for the current ATLAS Sky station.

    This service never schedules captures. It only ranks passes so a later
    scheduler can make conflict-aware decisions.
    """

    def __init__(
        self,
        catalog_path: Path | str | None = None,
        output_path: Path | str | None = None,
    ):
        self.catalog_path = Path(
            catalog_path
            or DEFAULT_CATALOG_PATH
        )

        self.output_path = Path(
            output_path
            or DEFAULT_OPPORTUNITIES_PATH
        )

    def load(
        self,
    ) -> dict[str, Any]:
        if not self.output_path.exists():
            return {
                "generated_at": None,
                "opportunities": [],
            }

        try:
            payload = json.loads(
                self.output_path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ):
            return {
                "generated_at": None,
                "opportunities": [],
            }

        if not isinstance(
            payload,
            dict,
        ):
            return {
                "generated_at": None,
                "opportunities": [],
            }

        payload.setdefault(
            "opportunities",
            [],
        )

        return payload

    def build(
        self,
        *,
        latitude_deg: float,
        longitude_deg: float,
        altitude_m: float,
        horizon_hours: int = 24,
        min_elevation_deg: float = 15.0,
        max_spacecraft: int = 120,
        max_results: int = 40,
    ) -> dict[str, Any]:
        try:
            from skyfield.api import (
                EarthSatellite,
                load,
                wgs84,
            )
        except ImportError as exc:
            raise RuntimeError(
                "skyfield is required to build orbital opportunities"
            ) from exc

        catalog = self._load_catalog()

        transmitters = self._best_transmitters(
            catalog.get(
                "targets",
                [],
            ),
            max_spacecraft=max_spacecraft,
        )

        tle_map = self._fetch_active_tles()

        ts = load.timescale()

        local_tz = ZoneInfo(
            os.getenv(
                "ATLAS_SKY_TIMEZONE",
                "America/Argentina/San_Juan",
            )
        )

        observer = wgs84.latlon(
            latitude_deg,
            longitude_deg,
            elevation_m=altitude_m,
        )

        start_dt = datetime.now(
            timezone.utc
        )

        end_dt = (
            start_dt
            + timedelta(
                hours=horizon_hours
            )
        )

        t0 = ts.from_datetime(
            start_dt
        )

        t1 = ts.from_datetime(
            end_dt
        )

        opportunities = []

        missing_tle = []

        for target in transmitters:
            norad = target.get(
                "norad_id"
            )

            if not norad:
                continue

            tle = tle_map.get(
                int(norad)
            )

            if tle is None:
                missing_tle.append(
                    int(norad)
                )
                continue

            sat = EarthSatellite(
                tle["line1"],
                tle["line2"],
                tle["name"],
                ts,
            )

            times, events = sat.find_events(
                observer,
                t0,
                t1,
                altitude_degrees=(
                    min_elevation_deg
                ),
            )

            current = None

            for time, event in zip(
                times,
                events,
            ):
                dt = (
                    time.utc_datetime()
                    .astimezone(
                        timezone.utc
                    )
                )

                if event == 0:
                    current = {
                        "aos_utc": dt,
                    }

                elif (
                    event == 1
                    and current is not None
                ):
                    alt, _, _ = (
                        (sat-observer)
                        .at(time)
                        .altaz()
                    )

                    current[
                        "max_time_utc"
                    ] = dt

                    current[
                        "max_elevation_deg"
                    ] = float(
                        alt.degrees
                    )

                elif (
                    event == 2
                    and current is not None
                ):
                    current[
                        "los_utc"
                    ] = dt

                    if (
                        "max_elevation_deg"
                        in current
                    ):
                        opportunities.append(
                            self._opportunity(
                                target,
                                current,
                                local_tz=local_tz,
                            )
                        )

                    current = None

        opportunities.sort(
            key=lambda item: (
                -item[
                    "opportunity_score"
                ],
                item["aos_utc"],
            )
        )

        selected = self._diversify(
            opportunities,
            max_results=max_results,
        )

        payload = {
            "schema": "atlas-sky-opportunities/v1",
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "window_start_utc": (
                start_dt.isoformat()
            ),
            "window_end_utc": (
                end_dt.isoformat()
            ),
            "station": {
                "latitude_deg": (
                    latitude_deg
                ),
                "longitude_deg": (
                    longitude_deg
                ),
                "altitude_m": altitude_m,
            },
            "minimum_elevation_deg": (
                min_elevation_deg
            ),
            "catalog_spacecraft_considered": (
                len(transmitters)
            ),
            "missing_tle": sorted(
                set(missing_tle)
            ),
            "opportunities": selected,
        }

        self.output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.output_path.write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            ) + "\n",
            encoding="utf-8",
        )

        return payload

    def _load_catalog(
        self,
    ) -> dict[str, Any]:
        if not self.catalog_path.exists():
            raise FileNotFoundError(
                self.catalog_path
            )

        payload = json.loads(
            self.catalog_path.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "Invalid ATLAS Sky catalog"
            )

        return payload

    @staticmethod
    def _best_transmitters(
        targets: list[dict[str, Any]],
        *,
        max_spacecraft: int,
    ) -> list[dict[str, Any]]:
        best: dict[Any, dict[str, Any]] = {}

        for item in targets:
            if not item.get(
                "current_antenna_candidate"
            ):
                continue

            norad = item.get(
                "norad_id"
            )

            if not norad:
                continue

            current = best.get(
                norad
            )

            if (
                current is None
                or int(
                    item.get(
                        "priority_score",
                        0,
                    )
                )
                > int(
                    current.get(
                        "priority_score",
                        0,
                    )
                )
            ):
                best[
                    norad
                ] = item

        ranked = sorted(
            best.values(),
            key=lambda item: (
                -int(
                    item.get(
                        "priority_score",
                        0,
                    )
                ),
                item.get(
                    "satellite_name",
                    "",
                ),
            ),
        )

        return ranked[
            :max_spacecraft
        ]

    @staticmethod
    def _fetch_active_tles(
    ) -> dict[int, dict[str, str]]:
        req = Request(
            CELESTRAK_ACTIVE_TLE,
            headers={
                "User-Agent": "ATLAS-SKY/0.4",
            },
        )

        text = (
            urlopen(
                req,
                timeout=30,
            )
            .read()
            .decode(
                "utf-8",
                errors="replace",
            )
        )

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        result: dict[
            int,
            dict[str, str],
        ] = {}

        index = 0

        while index + 2 < len(lines):
            name = lines[index]
            line1 = lines[
                index+1
            ]
            line2 = lines[
                index+2
            ]

            if (
                line1.startswith("1 ")
                and line2.startswith("2 ")
            ):
                raw_norad = (
                    line1[2:7]
                    .strip()
                )

                try:
                    norad = int(
                        raw_norad
                    )
                except ValueError:
                    index += 3
                    continue

                result[norad] = {
                    "name": name,
                    "line1": line1,
                    "line2": line2,
                }

                index += 3

            else:
                index += 1

        return result

    @staticmethod
    def _opportunity(
        target: dict[str, Any],
        pass_data: dict[str, Any],
        *,
        local_tz: ZoneInfo,
    ) -> dict[str, Any]:
        product = _expected_product(
            str(
                target.get(
                    "mode",
                    "",
                )
            ),
            target.get(
                "description"
            ),
        )

        max_elevation = float(
            pass_data[
                "max_elevation_deg"
            ]
        )

        opportunity_score = (
            int(
                target.get(
                    "priority_score",
                    0,
                )
            )
            + _pass_bonus(
                max_elevation_deg=(
                    max_elevation
                ),
                product=product,
            )
        )

        aos = pass_data[
            "aos_utc"
        ]

        maximum = pass_data[
            "max_time_utc"
        ]

        los = pass_data[
            "los_utc"
        ]

        return {
            "satellite_name": target.get(
                "satellite_name"
            ),
            "norad_id": target.get(
                "norad_id"
            ),
            "frequency_mhz": target.get(
                "downlink_mhz"
            ),
            "mode": target.get(
                "mode"
            ),
            "baud": target.get(
                "baud"
            ),
            "description": target.get(
                "description"
            ),
            "service": target.get(
                "service"
            ),
            "reception_level": target.get(
                "reception_level"
            ),
            "reception_score": target.get(
                "reception_score"
            ),
            "catalog_priority": target.get(
                "priority_score"
            ),
            "expected_product": product,
            "activity_note": (
                "El transmisor está catalogado; la actividad durante "
                "este pase no está garantizada hasta comprobarla."
            ),
            "aos_utc": aos.isoformat(),
            "max_time_utc": (
                maximum.isoformat()
            ),
            "los_utc": los.isoformat(),
            "aos_local": (
                aos.astimezone(
                    local_tz
                ).isoformat()
            ),
            "max_time_local": (
                maximum.astimezone(
                    local_tz
                ).isoformat()
            ),
            "los_local": (
                los.astimezone(
                    local_tz
                ).isoformat()
            ),
            "duration_s": int(
                round(
                    (
                        los
                        - aos
                    ).total_seconds()
                )
            ),
            "max_elevation_deg": round(
                max_elevation,
                2,
            ),
            "opportunity_score": (
                opportunity_score
            ),
        }

    @staticmethod
    def _diversify(
        opportunities: list[dict[str, Any]],
        *,
        max_results: int,
    ) -> list[dict[str, Any]]:
        selected = []

        per_spacecraft: dict[
            Any,
            int,
        ] = {}

        for item in opportunities:
            key = item.get(
                "norad_id"
            )

            if per_spacecraft.get(
                key,
                0,
            ) >= 2:
                continue

            selected.append(
                item
            )

            per_spacecraft[key] = (
                per_spacecraft.get(
                    key,
                    0,
                )
                + 1
            )

            if (
                len(selected)
                >= max_results
            ):
                break

        return selected
