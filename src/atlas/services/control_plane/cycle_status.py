import json
import sqlite3

from datetime import (
    UTC,
    datetime,
)

from pathlib import Path

from atlas.storage.database import (
    Database,
    configured_database_path,
)


class OperationalCycleStatusStore:
    """
    Persist the latest ATLAS background operational-cycle state.

    This is control-plane telemetry, not infrastructure health.

    The singleton row answers questions such as:

        - Did the collector start a cycle?
        - Did the latest cycle finish?
        - Did it fail?
        - When was the last successful cycle?
        - Was Discovery authoritative?
        - What inventory reconciliation did it produce?
    """

    def __init__(
        self,
        database_path: str | Path | None = None,
    ):

        self.database_path = (
            Path(database_path)
            if database_path is not None
            else None
        )


    def _database(
        self,
    ):

        return Database(
            path=self.database_path
        )


    @staticmethod
    def _timestamp(
        value=None,
    ):

        if value is not None:
            return value

        return (
            datetime.now(
                UTC
            ).isoformat()
        )


    def mark_started(
        self,
        timestamp=None,
    ):

        now = self._timestamp(
            timestamp
        )

        with self._database() as db:

            db.conn.execute(
                """
                INSERT INTO operational_cycle_status
                (
                    id,
                    state,
                    started_at,
                    completed_at,
                    updated_at
                )
                VALUES
                (
                    1,
                    'RUNNING',
                    ?,
                    NULL,
                    ?
                )

                ON CONFLICT(id)
                DO UPDATE SET

                    state =
                        'RUNNING',

                    started_at =
                        excluded.started_at,

                    completed_at =
                        NULL,

                    updated_at =
                        excluded.updated_at
                """,
                (
                    now,
                    now,
                ),
            )

            db.conn.commit()


    def mark_success(
        self,
        result,
        timestamp=None,
    ):

        now = self._timestamp(
            timestamp
        )

        result = (
            result
            if isinstance(
                result,
                dict,
            )
            else {}
        )

        discovery = result.get(
            "discovery"
        )

        reconciliation = result.get(
            "reconciliation"
        )

        discovery_complete = (
            getattr(
                discovery,
                "complete",
                None,
            )
            if discovery is not None
            else None
        )

        discovery_assets = (
            getattr(
                discovery,
                "count",
                None,
            )
            if discovery is not None
            else None
        )

        if (
            discovery is not None
            and discovery_assets is None
        ):

            assets = getattr(
                discovery,
                "assets",
                None,
            )

            if assets is not None:

                discovery_assets = len(
                    assets
                )

        discovery_errors = (
            list(
                getattr(
                    discovery,
                    "errors",
                    [],
                )
                or []
            )
            if discovery is not None
            else []
        )

        counts = {}

        transitions = None

        if isinstance(
            reconciliation,
            dict,
        ):

            counts = (
                reconciliation.get(
                    "counts",
                    {}
                )
                or {}
            )

            transitions = len(
                reconciliation.get(
                    "transitions",
                    []
                )
                or []
            )

        active = counts.get(
            "ACTIVE"
        )

        stale = counts.get(
            "STALE"
        )

        retired = counts.get(
            "RETIRED"
        )

        encoded_errors = json.dumps(
            discovery_errors,
            ensure_ascii=False,
        )

        complete_value = (
            int(
                bool(
                    discovery_complete
                )
            )
            if discovery_complete
            is not None
            else None
        )

        with self._database() as db:

            db.conn.execute(
                """
                INSERT INTO operational_cycle_status
                (
                    id,
                    state,
                    started_at,
                    completed_at,
                    last_success_at,
                    last_error,
                    last_discovery_at,
                    last_discovery_complete,
                    last_discovery_assets,
                    last_discovery_errors_json,
                    active,
                    stale,
                    retired,
                    transitions,
                    updated_at
                )
                VALUES
                (
                    1,
                    'SUCCESS',
                    NULL,
                    ?,
                    ?,
                    NULL,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )

                ON CONFLICT(id)
                DO UPDATE SET

                    state =
                        'SUCCESS',

                    completed_at =
                        excluded.completed_at,

                    last_success_at =
                        excluded.last_success_at,

                    last_error =
                        NULL,

                    last_discovery_at =
                        excluded.last_discovery_at,

                    last_discovery_complete =
                        excluded.last_discovery_complete,

                    last_discovery_assets =
                        excluded.last_discovery_assets,

                    last_discovery_errors_json =
                        excluded.last_discovery_errors_json,

                    active =
                        excluded.active,

                    stale =
                        excluded.stale,

                    retired =
                        excluded.retired,

                    transitions =
                        excluded.transitions,

                    updated_at =
                        excluded.updated_at
                """,
                (
                    now,
                    now,
                    now,
                    complete_value,
                    discovery_assets,
                    encoded_errors,
                    active,
                    stale,
                    retired,
                    transitions,
                    now,
                ),
            )

            db.conn.commit()


    def mark_failed(
        self,
        error,
        timestamp=None,
    ):

        now = self._timestamp(
            timestamp
        )

        error_text = str(
            error
        )

        with self._database() as db:

            db.conn.execute(
                """
                INSERT INTO operational_cycle_status
                (
                    id,
                    state,
                    completed_at,
                    last_error,
                    updated_at
                )
                VALUES
                (
                    1,
                    'FAILED',
                    ?,
                    ?,
                    ?
                )

                ON CONFLICT(id)
                DO UPDATE SET

                    state =
                        'FAILED',

                    completed_at =
                        excluded.completed_at,

                    last_error =
                        excluded.last_error,

                    updated_at =
                        excluded.updated_at
                """,
                (
                    now,
                    error_text,
                    now,
                ),
            )

            db.conn.commit()


    def get(
        self,
    ):
        """
        Read the persisted singleton without invoking Database(),
        migrations or schema creation.

        Self-health HTTP reads must remain strictly read-only.
        """

        path = (
            self.database_path
            if self.database_path is not None
            else configured_database_path()
        )

        path = Path(
            path
        )

        if not path.exists():
            return None

        resolved = path.resolve()

        connection = sqlite3.connect(
            f"file:{resolved}?mode=ro",
            uri=True,
            timeout=5,
        )

        try:

            row = connection.execute(
                """
                SELECT
                    state,
                    started_at,
                    completed_at,
                    last_success_at,
                    last_error,
                    last_discovery_at,
                    last_discovery_complete,
                    last_discovery_assets,
                    last_discovery_errors_json,
                    active,
                    stale,
                    retired,
                    transitions,
                    updated_at

                FROM operational_cycle_status

                WHERE id = 1
                """
            ).fetchone()

        except sqlite3.OperationalError as exc:

            if (
                "no such table"
                in str(exc).lower()
            ):
                return None

            raise

        finally:
            connection.close()

        if row is None:
            return None

        (
            state,
            started_at,
            completed_at,
            last_success_at,
            last_error,
            last_discovery_at,
            last_discovery_complete,
            last_discovery_assets,
            last_discovery_errors_json,
            active,
            stale,
            retired,
            transitions,
            updated_at,
        ) = row

        try:

            discovery_errors = json.loads(
                last_discovery_errors_json
                or "[]"
            )

        except (
            TypeError,
            ValueError,
        ):

            discovery_errors = []

        return {
            "state":
                state,

            "started_at":
                started_at,

            "completed_at":
                completed_at,

            "last_success_at":
                last_success_at,

            "last_error":
                last_error,

            "discovery": {
                "observed_at":
                    last_discovery_at,

                "complete":
                    (
                        bool(
                            last_discovery_complete
                        )
                        if last_discovery_complete
                        is not None
                        else None
                    ),

                "assets":
                    last_discovery_assets,

                "errors":
                    discovery_errors,
            },

            "inventory": {
                "active":
                    active,

                "stale":
                    stale,

                "retired":
                    retired,

                "transitions":
                    transitions,
            },

            "updated_at":
                updated_at,
        }
