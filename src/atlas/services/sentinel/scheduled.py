import os
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path

from atlas.services.sentinel.runtime import (
    SentinelRuntime,
)
from atlas.services.sentinel.state import (
    SentinelStateStore,
)
from atlas.services.sentinel.telegram import (
    TelegramNotifier,
)


DEFAULT_SOURCE_DB = (
    "/opt/atlas/atlas.db"
)

DEFAULT_STATE_PATH = (
    "/var/lib/atlas/sentinel/"
    "state.json"
)


def _snapshot_database(
    source_path,
    *,
    directory=None,
):
    source_path = Path(
        source_path
    )

    if not source_path.is_file():
        raise FileNotFoundError(
            f"Sentinel source database "
            f"not found: {source_path}"
        )

    if directory is not None:
        Path(
            directory
        ).mkdir(
            parents=True,
            exist_ok=True,
        )

    fd, target_name = tempfile.mkstemp(
        prefix="atlas-sentinel-",
        suffix=".db",
        dir=directory,
    )

    os.close(
        fd
    )

    target_path = Path(
        target_name
    )

    source = None
    target = None

    try:
        source = sqlite3.connect(
            f"file:{source_path}?mode=ro",
            uri=True,
        )

        target = sqlite3.connect(
            target_path
        )

        source.backup(
            target
        )

        target.commit()

        check = target.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if check != "ok":
            raise RuntimeError(
                "Sentinel database snapshot "
                "integrity check failed"
            )

        return target_path

    except Exception:
        target_path.unlink(
            missing_ok=True
        )

        raise

    finally:
        if target is not None:
            target.close()

        if source is not None:
            source.close()


def _remove_snapshot(
    snapshot_path,
):
    snapshot_path = Path(
        snapshot_path
    )

    for path in (
        snapshot_path,
        Path(
            str(snapshot_path)
            + "-wal"
        ),
        Path(
            str(snapshot_path)
            + "-shm"
        ),
    ):
        path.unlink(
            missing_ok=True
        )


@contextmanager
def sentinel_database_snapshot(
    source_path,
    *,
    directory=None,
):
    """
    Present Sentinel with a disposable SQLite snapshot.

    Sentinel's inherited ATLAS repositories are therefore
    free to initialize their Database objects without ever
    opening the live production database for writes.
    """

    previous = os.environ.get(
        "ATLAS_DB_PATH"
    )

    snapshot_path = (
        _snapshot_database(
            source_path,
            directory=directory,
        )
    )

    try:
        os.environ[
            "ATLAS_DB_PATH"
        ] = str(
            snapshot_path
        )

        yield snapshot_path

    finally:
        if previous is None:
            os.environ.pop(
                "ATLAS_DB_PATH",
                None,
            )
        else:
            os.environ[
                "ATLAS_DB_PATH"
            ] = previous

        _remove_snapshot(
            snapshot_path
        )


def main():
    source_database = (
        os.environ.get(
            "ATLAS_SENTINEL_SOURCE_DB"
        )
        or os.environ.get(
            "ATLAS_DB_PATH"
        )
        or DEFAULT_SOURCE_DB
    )

    state_path = (
        os.environ.get(
            "ATLAS_SENTINEL_STATE_PATH"
        )
        or DEFAULT_STATE_PATH
    )

    snapshot_directory = (
        os.environ.get(
            "ATLAS_SENTINEL_SNAPSHOT_DIR"
        )
        or None
    )

    print(
        "ATLAS SENTINEL · "
        "SCHEDULED LIVE RUN"
    )

    print(
        "SOURCE DATABASE:",
        source_database,
    )

    with sentinel_database_snapshot(
        source_database,
        directory=snapshot_directory,
    ) as snapshot_path:

        print(
            "DATABASE SNAPSHOT:",
            snapshot_path,
        )

        #
        # Construct ATLAS sources only after ATLAS_DB_PATH
        # points at the disposable snapshot.
        #
        runtime = SentinelRuntime(
            state_store=(
                SentinelStateStore(
                    state_path
                )
            ),
            notifier=(
                TelegramNotifier()
            ),
        )

        result = runtime.run(
            dry_run=False
        )

        evaluation = (
            result.live_result.evaluation
        )

        print(
            "ACTIVE FINDINGS:",
            len(
                evaluation.observations
            ),
        )

        print(
            "NOTIFICATIONS:",
            len(
                evaluation.notifications
            ),
        )

        print(
            "DELIVERED:",
            len(
                result.delivered
            ),
        )

        print(
            "STATE SAVED:",
            (
                "YES"
                if result.state_saved
                else "NO"
            ),
        )

    print(
        "DATABASE SNAPSHOT: REMOVED"
    )


if __name__ == "__main__":
    main()
