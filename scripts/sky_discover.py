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
                "candidatos_antena_actual": len(
                    candidates
                ),
                "mejores_candidatos": (
                    candidates[:20]
                ),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
