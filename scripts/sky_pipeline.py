#!/usr/bin/env python3

import argparse
import json
import os
from pathlib import Path

from atlas.services.sky.pipeline import SkyPipelineService


DEFAULT_ROOT = Path(
    os.getenv(
        "ATLAS_SKY_OBSERVATIONS_ROOT",
        "/mnt/datos12tb/atlas-sky/observations",
    )
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Discover archived ATLAS Sky captures, "
            "verify archive integrity and publish "
            "observation manifests."
        )
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
    )

    args = parser.parse_args()

    results = (
        SkyPipelineService(
            args.root
        ).scan()
    )

    print(
        json.dumps(
            {
                "root": str(
                    args.root
                ),
                "observations": results,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
