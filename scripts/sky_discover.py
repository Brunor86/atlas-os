#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from atlas.services.sky.discovery import (
    DEFAULT_CATALOG_PATH,
    SkyDiscoveryService,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Actualiza el catálogo abierto de objetivos de ATLAS Sky "
            "desde SatNOGS DB y lo guarda localmente."
        )
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_CATALOG_PATH,
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=100,
    )

    args = parser.parse_args()

    result = SkyDiscoveryService(
        args.output
    ).refresh(
        max_pages=args.max_pages
    )

    targets = result.get(
        "targets",
        [],
    )

    candidates = [
        item
        for item in targets
        if item.get(
            "current_antenna_candidate"
        )
    ]

    best_by_spacecraft = {}

    for item in candidates:
        key = (
            item.get("norad_id")
            or item.get("satellite_name")
        )

        current = best_by_spacecraft.get(
            key
        )

        if (
            current is None
            or item.get(
                "priority_score",
                0,
            )
            > current.get(
                "priority_score",
                0,
            )
        ):
            best_by_spacecraft[
                key
            ] = item

    best_spacecraft = sorted(
        best_by_spacecraft.values(),
        key=lambda item: (
            -item.get(
                "priority_score",
                0,
            ),
            item.get(
                "satellite_name",
                "",
            ),
        ),
    )

    print(
        json.dumps(
            {
                "catalogo": str(
                    args.output
                ),
                "generado": result.get(
                    "generated_at"
                ),
                "transmisores_en_rango": len(
                    targets
                ),
                "naves_en_rango": result.get(
                    "spacecraft_count",
                    0,
                ),
                "transmisores_candidatos": len(
                    candidates
                ),
                "naves_candidatas_antena_actual": result.get(
                    "candidate_spacecraft_count",
                    0,
                ),
                "mejores_naves": (
                    best_spacecraft[:20]
                ),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
