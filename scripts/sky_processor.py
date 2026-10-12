#!/usr/bin/env python3

import argparse
import json
import os
from pathlib import Path

from atlas.services.sky.processor import (
    SkyProcessorService,
)


DEFAULT_ROOT = Path(
    os.getenv(
        "ATLAS_SKY_OBSERVATIONS_ROOT",
        "/mnt/datos12tb/atlas-sky/observations",
    )
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Incrementally process archived "
            "ATLAS Sky observations."
        )
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
    )

    parser.add_argument(
        "--satdump",
        default=os.getenv(
            "ATLAS_SKY_SATDUMP",
            "satdump",
        ),
    )

    parser.add_argument(
        "--retry-failed",
        action="store_true",
    )

    args = parser.parse_args()

    service = SkyProcessorService(
        args.root,
        satdump_command=args.satdump,
        retry_failed=args.retry_failed,
    )

    print(
        json.dumps(
            {
                "root": str(args.root),
                "observations": service.scan(),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
