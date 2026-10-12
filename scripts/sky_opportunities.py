#!/usr/bin/env python3

import argparse
import json
import os

from atlas.services.sky.opportunities import (
    SkyOpportunityService,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Calcula los mejores pases reales para ATLAS Sky "
            "a partir del catálogo abierto."
        )
    )

    parser.add_argument(
        "--hours",
        type=int,
        default=24,
    )

    parser.add_argument(
        "--min-elevation",
        type=float,
        default=15.0,
    )

    parser.add_argument(
        "--max-spacecraft",
        type=int,
        default=120,
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=30,
    )

    args = parser.parse_args()

    latitude = float(
        os.getenv(
            "ATLAS_SKY_LAT",
            "-31.54",
        )
    )

    longitude = float(
        os.getenv(
            "ATLAS_SKY_LON",
            "-68.54",
        )
    )

    altitude = float(
        os.getenv(
            "ATLAS_SKY_ALT_M",
            "650",
        )
    )

    result = SkyOpportunityService().build(
        latitude_deg=latitude,
        longitude_deg=longitude,
        altitude_m=altitude,
        horizon_hours=args.hours,
        min_elevation_deg=(
            args.min_elevation
        ),
        max_spacecraft=(
            args.max_spacecraft
        ),
        max_results=args.max_results,
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
