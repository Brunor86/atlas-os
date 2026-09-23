import os
import sqlite3
from contextlib import closing
from datetime import datetime, UTC
from functools import wraps
from pathlib import Path
from threading import RLock

from atlas.storage.migrations import migrate


DB_PATH = Path("atlas.db")


def serialized_connection(method):

    @wraps(method)
    def wrapper(
        self,
        *args,
        **kwargs,
    ):

        with self._conn_lock:
            return method(
                self,
                *args,
                **kwargs,
            )

    return wrapper


def configured_database_path() -> Path:
    """
    Resolve the ATLAS SQLite database path.

    Production defaults to ./atlas.db.

    Tests, isolated runtimes and future ATLAS OS instances can
    provide ATLAS_DB_PATH without changing repository code.
    """

    value = os.environ.get(
        "ATLAS_DB_PATH"
    )

    if value:
        return Path(value)

    return DB_PATH


class Database:


    def __init__(
        self,
        path: str | Path | None = None,
    ):

        self.path = (
            Path(path)
            if path is not None
            else configured_database_path()
        )

        if (
            self.path.parent
            != Path(".")
        ):
            self.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        self._conn_lock = RLock()

        self.conn = sqlite3.connect(
            self.path,
            timeout=30,
            check_same_thread=False,
        )

        self.conn.execute(
            "PRAGMA journal_mode=WAL;"
        )

        self.conn.execute(
            "PRAGMA busy_timeout=30000;"
        )

        self.create_tables()

        migrate(self.conn)


    def close(self):
        """
        Close the SQLite connection owned by this Database instance.

        Closing is idempotent so callers may safely use explicit
        cleanup from finally blocks and context managers.
        """

        connection = getattr(
            self,
            "conn",
            None,
        )

        if connection is None:
            return

        lock = getattr(
            self,
            "_conn_lock",
            None,
        )

        if lock is None:
            self.conn = None
            connection.close()
            return

        with lock:

            if self.conn is None:
                return

            connection = self.conn
            self.conn = None

            connection.close()


    def __enter__(self):

        return self


    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):

        self.close()

        return False


    def __del__(self):
        """
        Best-effort compatibility safety net.

        Explicit close/context management remains the preferred
        lifecycle contract.
        """

        try:
            self.close()

        except Exception:
            pass



    def create_tables(self):

        cursor = self.conn.cursor()


        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                created_at TEXT NOT NULL,

                data TEXT NOT NULL

            )
            """
        )


        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS events (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                type TEXT NOT NULL,

                title TEXT NOT NULL,

                message TEXT NOT NULL,

                first_seen TEXT NOT NULL,

                last_seen TEXT NOT NULL,

                status TEXT NOT NULL,

                event_key TEXT,

                severity TEXT DEFAULT 'warning',

                category TEXT DEFAULT 'system',

                occurrences INTEGER DEFAULT 1,

                asset_id TEXT

            )
            """
        )


        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS assets (

                id TEXT PRIMARY KEY,

                name TEXT NOT NULL,

                type TEXT NOT NULL,

                status TEXT NOT NULL,

                health REAL NOT NULL,

                criticality TEXT NOT NULL,

                last_seen TEXT NOT NULL,

                identity_json TEXT

            )
            """
        )


        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS observations (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                asset_id TEXT NOT NULL,

                type TEXT NOT NULL,

                value TEXT,

                severity TEXT NOT NULL,

                source TEXT NOT NULL,

                timestamp TEXT NOT NULL

            )
            """
        )

        #
        # Observation history uniqueness
        #
        # Prevent identical observation events from being
        # persisted more than once at the database level.
        #

        cursor.execute(
            '''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_observations_unique_event
            ON observations(
                asset_id,
                type,
                severity,
                source,
                timestamp,
                value
            )
            '''
        )



        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS health_findings (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                asset_id TEXT NOT NULL,

                finding_key TEXT UNIQUE NOT NULL,

                severity TEXT NOT NULL,

                title TEXT NOT NULL,

                message TEXT NOT NULL,

                category TEXT NOT NULL,

                status TEXT NOT NULL DEFAULT 'active',

                occurrences INTEGER DEFAULT 1,

                created_at TEXT NOT NULL,

                last_seen TEXT NOT NULL,

                resolved_at TEXT

            )
            """
        )



        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS action_requests (

                id TEXT PRIMARY KEY,

                action TEXT NOT NULL,

                target TEXT NOT NULL,

                risk TEXT NOT NULL,

                rollback TEXT,

                status TEXT NOT NULL,

                created_at TEXT NOT NULL,

                approved_by TEXT,

                approved_at TEXT

            )
            """
        )



        cursor.execute(
            """
            PRAGMA table_info(action_requests)
            """
        )

        columns = [
            row[1]
            for row in cursor.fetchall()
        ]


        if "incident_id" not in columns:

            cursor.execute(
                """
                ALTER TABLE action_requests
                ADD COLUMN incident_id TEXT
                """
            )


        if "incident_fingerprint" not in columns:

            cursor.execute(
                """
                ALTER TABLE action_requests
                ADD COLUMN incident_fingerprint TEXT
                """
            )



        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS action_history (

                id TEXT PRIMARY KEY,

                approval_id TEXT,

                action TEXT,

                target TEXT,

                status TEXT,

                result TEXT,

                executed_at TEXT

            )
            """
        )



        # Reserve an approval before sending an infrastructure command.
        # Claims are deliberately never released: an interrupted execution
        # may already have affected the target even without a history row.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS action_execution_claims (
                approval_id TEXT PRIMARY KEY NOT NULL,
                claimed_at TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS action_verifications (

                approval_id TEXT PRIMARY KEY NOT NULL,

                status TEXT NOT NULL,

                action TEXT NOT NULL,

                target TEXT NOT NULL,

                expected_state TEXT,

                observed_state TEXT,

                detail TEXT,

                evidence TEXT,

                verified_at TEXT NOT NULL

            )
            """
        )


        # Append-only audit trail for every verification attempt.
        #
        # action_verifications remains the authoritative latest state.
        # This table preserves how that state was reached.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS action_verification_history (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                approval_id TEXT NOT NULL,

                status TEXT NOT NULL,

                action TEXT NOT NULL,

                target TEXT NOT NULL,

                expected_state TEXT,

                observed_state TEXT,

                detail TEXT,

                evidence TEXT,

                verified_at TEXT NOT NULL,

                source TEXT NOT NULL,

                requested_by TEXT

            )
            """
        )


        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_action_verification_history_approval

            ON action_verification_history (
                approval_id,
                id
            )
            """
        )


        # Existing installations already have authoritative rows in
        # action_verifications. Seed their audit history once so deployment
        # of Manual Recovery V1 does not erase the origin of an existing
        # RECOVERY_REQUIRED / VERIFIED state.
        cursor.execute(
            """
            INSERT INTO action_verification_history (
                approval_id,
                status,
                action,
                target,
                expected_state,
                observed_state,
                detail,
                evidence,
                verified_at,
                source,
                requested_by
            )

            SELECT
                current.approval_id,
                current.status,
                current.action,
                current.target,
                current.expected_state,
                current.observed_state,
                current.detail,
                current.evidence,
                current.verified_at,
                'POST_EXECUTION',
                NULL

            FROM action_verifications AS current

            WHERE NOT EXISTS (
                SELECT 1

                FROM action_verification_history AS history

                WHERE history.approval_id =
                      current.approval_id
            )
            """
        )


        # Migration: add evidence column to action_history

        cursor.execute(
            """
            PRAGMA table_info(action_history)
            """
        )

        action_history_columns = [
            row[1]
            for row in cursor.fetchall()
        ]


        if "evidence" not in action_history_columns:

            cursor.execute(
                """
                ALTER TABLE action_history
                ADD COLUMN evidence TEXT
                """
            )


        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents (

                id TEXT PRIMARY KEY,

                title TEXT NOT NULL,

                asset TEXT NOT NULL,

                severity TEXT NOT NULL,

                status TEXT NOT NULL,

                evidence TEXT,

                recommendations TEXT,

                impact TEXT,

                created_at TEXT NOT NULL,

                updated_at TEXT NOT NULL

            )
            """
        )


        # Migration: add impact column to existing databases

        cursor.execute(
            """
            PRAGMA table_info(incidents)
            """
        )

        columns = [
            row[1]
            for row in cursor.fetchall()
        ]


        if "impact" not in columns:

            cursor.execute(
                """
                ALTER TABLE incidents
                ADD COLUMN impact TEXT
                """
            )


        extra_columns = {

            "root_cause": "TEXT",

            "diagnosis": "TEXT",

            "blast_radius": "TEXT",

            "suggested_actions": "TEXT",

              "impact_intelligence": "TEXT",

        }


        for name, dtype in extra_columns.items():

            if name not in columns:

                cursor.execute(
                    f"""
                    ALTER TABLE incidents
                    ADD COLUMN {name} {dtype}
                    """
                )


        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS learning_records (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                incident_id TEXT,

                action TEXT NOT NULL,

                result TEXT NOT NULL,

                resolution TEXT,

                confidence REAL,

                created_at TEXT NOT NULL

            )
            """
        )


        # Migration: add evidence column to learning_records

        cursor.execute(
            """
            PRAGMA table_info(learning_records)
            """
        )

        learning_columns = [
            row[1]
            for row in cursor.fetchall()
        ]


        if "evidence" not in learning_columns:

            cursor.execute(
                """
                ALTER TABLE learning_records
                ADD COLUMN evidence TEXT
                """
            )



        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS incident_lifecycle_events (

                id TEXT PRIMARY KEY,

                incident_id TEXT NOT NULL,

                state TEXT NOT NULL,

                detail TEXT NOT NULL,

                actor TEXT NOT NULL,

                timestamp TEXT NOT NULL

            )
            """
        )



        #
        # Migration: material lifecycle fingerprint.
        #
        # Automatic NOC transitions use this value to make
        # lifecycle persistence idempotent across repeated
        # evaluations of the same material incident state.
        #

        cursor.execute(
            """
            PRAGMA table_info(
                incident_lifecycle_events
            )
            """
        )

        lifecycle_columns = [
            row[1]
            for row in cursor.fetchall()
        ]

        if (
            "fingerprint"
            not in lifecycle_columns
        ):

            cursor.execute(
                """
                ALTER TABLE
                    incident_lifecycle_events
                ADD COLUMN
                    fingerprint TEXT
                """
            )


        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_incident_lifecycle_fingerprint
            ON incident_lifecycle_events
            (
                incident_id,
                state,
                fingerprint
            )
            """
        )


        #
        # ATLAS control-plane operational cycle status.
        #
        # Singleton row (id=1) records the latest background
        # collector execution independently from infrastructure
        # health snapshots.
        #
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS operational_cycle_status (

                id INTEGER PRIMARY KEY CHECK (id = 1),

                state TEXT NOT NULL DEFAULT 'UNKNOWN',

                started_at TEXT,

                completed_at TEXT,

                last_success_at TEXT,

                last_error TEXT,

                last_discovery_at TEXT,

                last_discovery_complete INTEGER,

                last_discovery_assets INTEGER,

                last_discovery_errors_json TEXT,

                active INTEGER,

                stale INTEGER,

                retired INTEGER,

                transitions INTEGER,

                updated_at TEXT NOT NULL

            )
            """
        )


        self.conn.commit()



    def save_snapshot(
        self,
        created_at,
        data,
    ):

        cursor = self.conn.cursor()


        cursor.execute(
            """
            INSERT INTO snapshots
            (
                created_at,
                data
            )

            VALUES
            (?,?)
            """,
            (
                created_at,
                data,
            )
        )


        self.conn.commit()



    def get_last_snapshot(self):

        cursor = self.conn.cursor()


        cursor.execute(
            """
            SELECT
                created_at,
                data

            FROM snapshots

            ORDER BY id DESC

            LIMIT 1
            """
        )


        return cursor.fetchone()



    def get_snapshots(
        self,
        limit=50,
    ):

        cursor = self.conn.cursor()


        cursor.execute(
            """
            SELECT
                id,
                created_at,
                data

            FROM snapshots

            ORDER BY id DESC

            LIMIT ?
            """,
            (
                limit,
            )
        )


        return cursor.fetchall()



    def save_event(
        self,
        event_type,
        title,
        message,
        first_seen,
        last_seen,
        status,
        event_key,
        severity="warning",
        category="system",
        occurrences=1,
        asset_id=None,
    ):

        cursor = self.conn.cursor()


        cursor.execute(
            """
            INSERT INTO events
            (
                type,
                title,
                message,
                first_seen,
                last_seen,
                status,
                event_key,
                severity,
                category,
                occurrences,
                asset_id
            )

            VALUES
            (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                event_type,
                title,
                message,
                first_seen,
                last_seen,
                status,
                event_key,
                severity,
                category,
                occurrences,
                asset_id,
            )
        )


        self.conn.commit()



    def increment_event(
        self,
        event_id,
        timestamp,
    ):

        cursor = self.conn.cursor()


        cursor.execute(
            """
            UPDATE events

            SET

                last_seen = ?,

                occurrences = occurrences + 1

            WHERE id = ?

            """,
            (
                timestamp,
                event_id,
            )
        )


        self.conn.commit()



    def refresh_event(
        self,
        event_id,
        event_type,
        title,
        message,
        timestamp,
        severity,
        category,
        asset_id,
    ):

        cursor = self.conn.cursor()


        cursor.execute(
            """
            UPDATE events

            SET
                type = ?,
                title = ?,
                message = ?,
                last_seen = ?,
                severity = ?,
                category = ?,
                asset_id = ?,
                occurrences = occurrences + 1

            WHERE id = ?
            """,
            (
                event_type,
                title,
                message,
                timestamp,
                severity,
                category,
                asset_id,
                event_id,
            )
        )


        self.conn.commit()



    def get_events(
        self,
        limit=100,
    ):

        cursor = self.conn.cursor()


        cursor.execute(
            """
            SELECT
                id,
                type,
                title,
                message,
                first_seen,
                last_seen,
                status,
                event_key,
                severity,
                category,
                occurrences,
                asset_id

            FROM events

            ORDER BY last_seen DESC

            LIMIT ?
            """,
            (
                limit,
            )
        )


        rows = cursor.fetchall()


        events = []


        for row in rows:

            events.append(
                {
                    "id": row[0],
                    "type": row[1],
                    "title": row[2],
                    "message": row[3],
                    "first_seen": row[4],
                    "last_seen": row[5],
                    "status": row[6],
                    "event_key": row[7],
                    "severity": row[8],
                    "category": row[9],
                    "occurrences": row[10],
                    "asset_id": row[11],
                }
            )


        return events



    def get_active_events(
        self,
    ):

        cursor = self.conn.cursor()


        cursor.execute(
            """
            SELECT
                id,
                type,
                title,
                message,
                first_seen,
                last_seen,
                status,
                event_key,
                severity,
                category,
                occurrences,
                asset_id

            FROM events

            WHERE status = 'open'

            ORDER BY last_seen DESC

            """
        )


        rows = cursor.fetchall()


        events = []


        for row in rows:

            events.append(
                {
                    "id": row[0],
                    "type": row[1],
                    "title": row[2],
                    "message": row[3],
                    "first_seen": row[4],
                    "last_seen": row[5],
                    "status": row[6],
                    "event_key": row[7],
                    "severity": row[8],
                    "category": row[9],
                    "occurrences": row[10],
                    "asset_id": row[11],
                }
            )


        return events



    def close_event(
        self,
        event_id,
        timestamp,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            UPDATE events

            SET
                status = 'closed',
                last_seen = ?

            WHERE id = ?
            """,
            (
                timestamp,
                event_id,
            )
        )

        self.conn.commit()



    def save_incident(
        self,
        incident,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT INTO incidents
            (
                id,
                title,
                asset,
                severity,
                status,
                evidence,
                recommendations,
                impact,
                  impact_intelligence,
                root_cause,
                diagnosis,
                blast_radius,
                suggested_actions,
                created_at,
                updated_at
            )

            VALUES
              (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                incident.id,
                incident.title,
                incident.asset,
                incident.severity,
                incident.status,
                str(incident.evidence),
                str(incident.recommendations),
                str(incident.impact),
                  str(incident.impact_intelligence),
                incident.root_cause,
                incident.diagnosis,
                str(incident.blast_radius),
                str(incident.suggested_actions),
                incident.created_at.isoformat(),
                incident.updated_at.isoformat(),
            )
        )

        self.conn.commit()



    def get_incidents(
        self,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                title,
                asset,
                severity,
                status,
                evidence,
                recommendations,
                impact,
                  impact_intelligence,
                root_cause,
                diagnosis,
                blast_radius,
                suggested_actions,
                created_at,
                updated_at

            FROM incidents

            ORDER BY
                CASE severity
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MEDIUM' THEN 3
                    WHEN 'WARNING' THEN 4
                    WHEN 'LOW' THEN 5
                    ELSE 6
                END,
                created_at DESC
            """
        )

        return cursor.fetchall()





    def count_incidents_by_status(
        self,
        status,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM incidents

            WHERE status=?
            """,
            (
                status,
            )
        )

        return cursor.fetchone()[0]



    def count_incidents_by_severity(
        self,
        severity,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM incidents

            WHERE severity=?
            """,
            (
                severity,
            )
        )

        return cursor.fetchone()[0]



    def count_incidents_by_title(
        self,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT
                title,
                COUNT(*) as total

            FROM incidents

            GROUP BY title

            ORDER BY total DESC
            """
        )

        return cursor.fetchall()


    def update_incident_status(
        self,
        incident_id,
        status,
        updated_at,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            UPDATE incidents

            SET
                status=?,
                updated_at=?

            WHERE id=?

            """,
            (
                status,
                updated_at,
                incident_id,
            )
        )

        self.conn.commit()


    def find_active_incident(
        self,
        title,
        asset,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                title,
                asset,
                severity,
                status,
                evidence,
                recommendations,
                impact,
                impact_intelligence,
                root_cause,
                diagnosis,
                blast_radius,
                suggested_actions,
                created_at,
                updated_at

            FROM incidents

            WHERE title = ?
            AND asset = ?
            AND status != 'RESOLVED'

            LIMIT 1
            """,
            (
                title,
                asset,
            )
        )

        return cursor.fetchone()



    def update_incident(
        self,
        incident_id,
        asset,
        severity,
        evidence,
        impact,
        impact_intelligence,
        root_cause,
        diagnosis,
        blast_radius,
        suggested_actions,
        updated_at,
    ):

        cursor = self.conn.cursor()


        cursor.execute(
            """
            SELECT evidence
            FROM incidents
            WHERE id=?
            """,
            (
                incident_id,
            )
        )


        row = cursor.fetchone()


        existing = []


        if row and row[0]:

            import ast

            try:
                existing = ast.literal_eval(
                    row[0]
                )

            except Exception:
                existing = []



        merged = list(existing)


        for item in evidence or []:

            if item not in merged:

                merged.append(item)



        cursor.execute(
            """
            UPDATE incidents

            SET
                asset=?,
                severity=?,
                evidence=?,
                impact=?,
                impact_intelligence=?,
                root_cause=?,
                diagnosis=?,
                blast_radius=?,
                suggested_actions=?,
                updated_at=?

            WHERE id=?

            """,
            (
                asset,
                severity,
                str(merged),
                str(impact),
                str(impact_intelligence),
                root_cause,
                diagnosis,
                str(blast_radius),
                str(suggested_actions),
                updated_at,
                incident_id,
            )
        )


        self.conn.commit()




    def save_incident_event(
        self,
        incident_id,
        timestamp,
        event_type,
        detail="",
        severity=None,
        impact=None,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT INTO incident_events
            (
                incident_id,
                timestamp,
                type,
                detail,
                severity,
                impact
            )

            VALUES (?, ?, ?, ?, ?, ?)

            """,
            (
                incident_id,
                timestamp,
                event_type,
                detail,
                severity,
                str(impact or []),
            )
        )

        self.conn.commit()



    def get_incident_events(
        self,
        incident_id,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                incident_id,
                timestamp,
                type,
                detail,
                severity,
                impact

            FROM incident_events

            WHERE incident_id=?

            ORDER BY timestamp ASC

            """,
            (
                incident_id,
            )
        )

        return cursor.fetchall()




    def save_incident_lifecycle(
        self,
        record,
    ):

        cursor = self.conn.cursor()


        cursor.execute(
            """
            INSERT INTO incident_lifecycle_events
            (
                id,
                incident_id,
                state,
                detail,
                actor,
                timestamp,
                fingerprint
            )

            VALUES (?, ?, ?, ?, ?, ?, ?)

            """,
            (
                record["id"],
                record["incident_id"],
                record["state"],
                record["detail"],
                record.get(
                    "actor",
                    "ATLAS",
                ),
                record["timestamp"],
                record.get(
                    "fingerprint"
                ),
            )
        )


        self.conn.commit()



    def has_incident_lifecycle_fingerprint(
        self,
        incident_id,
        state,
        fingerprint,
    ):

        if not fingerprint:
            return False

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT 1
            FROM incident_lifecycle_events
            WHERE incident_id=?
              AND state=?
              AND fingerprint=?
            LIMIT 1
            """,
            (
                incident_id,
                state,
                fingerprint,
            )
        )

        return (
            cursor.fetchone()
            is not None
        )



    def get_incident_lifecycle(
        self,
        incident_id,
    ):

        cursor = self.conn.cursor()


        cursor.execute(
            """
            SELECT
                id,
                incident_id,
                state,
                detail,
                actor,
                timestamp

            FROM incident_lifecycle_events

            WHERE incident_id=?

            ORDER BY timestamp ASC

            """,
            (
                incident_id,
            )
        )


        rows = cursor.fetchall()


        return [

            {
                "id": row[0],
                "incident_id": row[1],
                "state": row[2],
                "detail": row[3],
                "actor": row[4],
                "timestamp": row[5],
            }

            for row in rows

        ]



    def find_incident_history(
        self,
        title,
        asset,
    ):

        cursor = self.connection.cursor()


        cursor.execute(
            """
            SELECT *
            FROM incidents
            WHERE title=?
            AND asset=?
            ORDER BY created_at DESC
            """,
            (
                title,
                asset,
            )
        )


        return cursor.fetchall()



    def get_similar_incidents(
        self,
        asset,
        root_cause,
    ):

        cursor = self.conn.cursor()


        asset_search = f"%{asset}%"

        cause_search = f"%{root_cause}%"



        cursor.execute(
            """
            SELECT
                id,
                title,
                asset,
                severity,
                status,
                evidence,
                impact,
                root_cause,
                diagnosis,
                suggested_actions,
                created_at

            FROM incidents

            WHERE
                asset LIKE ?
                OR evidence LIKE ?
                OR root_cause LIKE ?
                OR diagnosis LIKE ?

            ORDER BY created_at DESC
            """,
            (
                asset_search,
                cause_search,
                cause_search,
                cause_search,
            )
        )


        return cursor.fetchall()


    def get_successful_learning_actions(
        self,
    ):

        cursor = self.conn.cursor()


        cursor.execute(
            """
            SELECT
                action,
                result,
                resolution,
                evidence

            FROM learning_records

            WHERE result='SUCCESS'

            ORDER BY created_at DESC
            """
        )


        return cursor.fetchall()




    @serialized_connection
    def save_action_request(
        self,
        action,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT INTO action_requests (

                id,
                incident_id,
                action,
                target,
                risk,
                rollback,
                status,
                created_at,
                approved_by,
                approved_at,
                incident_fingerprint

            )

            VALUES (?,?,?,?,?,?,?,?,?,?,?)

            """,
            (

                action["id"],
                action.get("incident_id"),
                action["action"],
                action["target"],
                action["risk"],
                action["rollback"],
                action["status"],
                action["created_at"],
                action["approved_by"],
                action["approved_at"],
                action.get(
                    "incident_fingerprint"
                ),

            )
        )

        self.conn.commit()



    @serialized_connection
    def list_action_requests(
        self,
        limit=50,
    ):

        safe_limit = max(
            1,
            min(
                int(limit or 50),
                100,
            ),
        )

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                incident_id,
                action,
                target,
                risk,
                rollback,
                status,
                created_at,
                approved_by,
                approved_at,
                incident_fingerprint

            FROM action_requests

            ORDER BY
                created_at DESC,
                rowid DESC

            LIMIT ?
            """,
            (
                safe_limit,
            ),
        )

        rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "incident_id": row[1],
                "action": row[2],
                "target": row[3],
                "risk": row[4],
                "rollback": row[5],
                "status": row[6],
                "created_at": row[7],
                "approved_by": row[8],
                "approved_at": row[9],
                "incident_fingerprint": row[10],
            }
            for row in rows
        ]


    @serialized_connection
    def get_action_request(
        self,
        action_id,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT

                id,
                incident_id,
                action,
                target,
                risk,
                rollback,
                status,
                created_at,
                approved_by,
                approved_at,
                incident_fingerprint

            FROM action_requests

            WHERE id=?

            """,
            (
                action_id,
            )
        )

        row = cursor.fetchone()

        if not row:
            return None

        return {

            "id": row[0],
            "incident_id": row[1],
            "action": row[2],
            "target": row[3],
            "risk": row[4],
            "rollback": row[5],
            "status": row[6],
            "created_at": row[7],
            "approved_by": row[8],
            "approved_at": row[9],
            "incident_fingerprint": row[10],

        }



    def claim_action_execution(self, approval_id):
        """Durably reserve one execution, including across processes.

        Use a dedicated, short-lived connection so concurrent API requests
        sharing this Database cannot commit or roll back each other's claim.
        The claim must commit before the caller invokes an external handler.
        """
        if str(self.path) == ":memory:":
            raise ValueError("action execution requires a persistent database")

        with closing(sqlite3.connect(self.path, timeout=30)) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO action_execution_claims (
                        approval_id, claimed_at
                    )
                    SELECT id, ?
                    FROM action_requests
                    WHERE id=?
                      AND status='APPROVED'
                      AND NOT EXISTS (
                          SELECT 1 FROM action_history
                          WHERE approval_id=action_requests.id
                      )
                    ON CONFLICT (approval_id) DO NOTHING
                    """,
                    (
                        datetime.now(UTC).isoformat(),
                        approval_id,
                    ),
                )
                claimed = cursor.rowcount == 1

        return claimed


    @serialized_connection
    def get_action_execution_state(
        self,
        approval_id,
    ):

        import ast

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT
                action_requests.id,
                action_requests.status,
                action_execution_claims.claimed_at,

                action_history.id,
                action_history.status,
                action_history.result,
                action_history.executed_at,

                action_verifications.status,
                action_verifications.action,
                action_verifications.target,
                action_verifications.expected_state,
                action_verifications.observed_state,
                action_verifications.detail,
                action_verifications.evidence,
                action_verifications.verified_at

            FROM action_requests

            LEFT JOIN action_execution_claims
                ON action_execution_claims.approval_id =
                   action_requests.id

            LEFT JOIN action_history
                ON action_history.rowid = (
                    SELECT rowid
                    FROM action_history
                    WHERE approval_id =
                          action_requests.id
                    ORDER BY
                        executed_at DESC,
                        rowid DESC
                    LIMIT 1
                )

            LEFT JOIN action_verifications
                ON action_verifications.approval_id =
                   action_requests.id

            WHERE action_requests.id=?
            """,
            (
                approval_id,
            ),
        )

        row = cursor.fetchone()

        if not row:
            return None


        action_status = row[1]
        claimed_at = row[2]
        history_id = row[3]
        verification_status = row[7]


        if verification_status == "VERIFIED":

            state = "VERIFIED"


        elif verification_status == "RECOVERY_REQUIRED":

            state = "RECOVERY_REQUIRED"


        elif action_status == "EXECUTION_FAILED":

            state = "EXECUTION_FAILED"


        elif history_id is not None:

            state = "RECORDED"


        elif claimed_at is not None:

            state = "RESERVED"


        elif action_status == "APPROVED":

            state = "READY"


        else:

            state = "NOT_READY"


        history = None

        if history_id is not None:

            history = {
                "id":
                    history_id,

                "status":
                    row[4],

                "result":
                    row[5],

                "executed_at":
                    row[6],
            }


        verification = None

        if verification_status is not None:

            evidence = []

            if row[13]:

                try:
                    evidence = ast.literal_eval(
                        row[13]
                    )

                except Exception:
                    evidence = [
                        str(
                            row[13]
                        )
                    ]


            verification = {
                "status":
                    row[7],

                "action":
                    row[8],

                "target":
                    row[9],

                "expected_state":
                    row[10],

                "observed_state":
                    row[11],

                "detail":
                    row[12],

                "evidence":
                    evidence,

                "verified_at":
                    row[14],
            }


        return {
            "approval_id":
                row[0],

            "action_status":
                action_status,

            "state":
                state,

            "claimed_at":
                claimed_at,

            "history":
                history,

            "verification":
                verification,
        }


    @serialized_connection
    def update_action_status(
        self,
        action_id,
        status,
        user,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            UPDATE action_requests

            SET

                status=?,

                approved_by=?,

                approved_at=datetime('now')

            WHERE id=?

            """,
            (
                status,
                user,
                action_id,
            )
        )

        self.conn.commit()


        return {

            "id": action_id,

            "status": status,

            "approved_by": user,

        }


    @serialized_connection
    def mark_action_executed(
        self,
        action_id,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            UPDATE action_requests

            SET status='EXECUTED'

            WHERE id=?

            """,
            (
                action_id,
            )
        )

        self.conn.commit()

        return {
            "id": action_id,
            "status": "EXECUTED",
        }


    @serialized_connection
    def get_pending_actions(
        self,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT

                id,
                incident_id,
                action,
                target,
                risk,
                rollback,
                status,
                created_at,
                approved_by,
                approved_at

            FROM action_requests

            WHERE status='PENDING_APPROVAL'

            ORDER BY created_at DESC

            """
        )

        return cursor.fetchall()



    @serialized_connection
    def get_action_requests_by_incident(
        self,
        incident_id,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                incident_id,
                action,
                target,
                risk,
                rollback,
                status,
                created_at,
                approved_by,
                approved_at,
                incident_fingerprint
            FROM action_requests
            WHERE incident_id=?
            ORDER BY created_at DESC
            """,
            (
                incident_id,
            )
        )

        rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "incident_id": row[1],
                "action": row[2],
                "target": row[3],
                "risk": row[4],
                "rollback": row[5],
                "status": row[6],
                "created_at": row[7],
                "approved_by": row[8],
                "approved_at": row[9],
                "incident_fingerprint": row[10],
            }
            for row in rows
        ]


    @serialized_connection
    def update_action_fingerprint(
        self,
        action_id,
        incident_fingerprint,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            UPDATE action_requests
            SET incident_fingerprint=?
            WHERE id=?
            """,
            (
                incident_fingerprint,
                action_id,
            )
        )

        self.conn.commit()

        return {
            "id": action_id,
            "incident_fingerprint":
                incident_fingerprint,
        }


    @serialized_connection
    def cancel_unexecuted_actions_for_incident(
        self,
        incident_id,
    ):
        """
        Cancel stale incident actions only when execution has
        definitely not started.

        Claimed or historically executed actions are deliberately
        untouched because their external outcome may already be
        committed or uncertain.
        """

        cursor = self.conn.cursor()

        cursor.execute(
            """
            UPDATE action_requests

            SET status='CANCELLED'

            WHERE incident_id=?

              AND status IN (
                  'PENDING_APPROVAL',
                  'APPROVED',
                  'AUTO_APPROVED'
              )

              AND NOT EXISTS (
                  SELECT 1
                  FROM action_execution_claims
                  WHERE
                      action_execution_claims.approval_id
                      = action_requests.id
              )

              AND NOT EXISTS (
                  SELECT 1
                  FROM action_history
                  WHERE
                      action_history.approval_id
                      = action_requests.id
              )
            """,
            (
                incident_id,
            )
        )

        cancelled = cursor.rowcount

        self.conn.commit()

        return cancelled


    @serialized_connection
    def set_action_status(
        self,
        action_id,
        status,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            UPDATE action_requests

            SET status=?

            WHERE id=?
            """,
            (
                status,
                action_id,
            )
        )

        self.conn.commit()

        return {
            "id":
                action_id,

            "status":
                status,
        }


    @serialized_connection
    def finalize_action_verification(
        self,
        record,
        action_status,
        *,
        expected_current_status=None,
    ):
        """
        Persist verification and final action state atomically.
        """

        cursor = self.conn.cursor()


        source = str(
            record.get(
                "source",
                "POST_EXECUTION",
            )
            or "POST_EXECUTION"
        )

        requested_by = (
            record.get(
                "requested_by"
            )
        )


        # Manual recovery must never overwrite a newer terminal state.
        #
        # Example:
        #   request A observes RUNNING -> VERIFIED
        #   request B had previously observed STOPPED
        #
        # If A commits first, B must not be allowed to move VERIFIED
        # back to RECOVERY_REQUIRED.
        if expected_current_status is not None:

            cursor.execute(
                """
                UPDATE action_requests

                SET status=?

                WHERE id=?
                  AND status=?
                """,
                (
                    action_status,
                    record["approval_id"],
                    expected_current_status,
                ),
            )

            if cursor.rowcount != 1:

                self.conn.rollback()

                return False


        cursor.execute(
            """
            INSERT INTO action_verification_history (
                approval_id,
                status,
                action,
                target,
                expected_state,
                observed_state,
                detail,
                evidence,
                verified_at,
                source,
                requested_by
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["approval_id"],
                record["status"],
                record["action"],
                record["target"],
                record.get(
                    "expected_state"
                ),
                record.get(
                    "observed_state"
                ),
                record.get(
                    "detail",
                    ""
                ),
                str(
                    record.get(
                        "evidence",
                        []
                    )
                ),
                record["verified_at"],
                source,
                requested_by,
            )
        )


        cursor.execute(
            """
            INSERT INTO action_verifications (
                approval_id,
                status,
                action,
                target,
                expected_state,
                observed_state,
                detail,
                evidence,
                verified_at
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(approval_id)
            DO UPDATE SET
                status=excluded.status,
                action=excluded.action,
                target=excluded.target,
                expected_state=excluded.expected_state,
                observed_state=excluded.observed_state,
                detail=excluded.detail,
                evidence=excluded.evidence,
                verified_at=excluded.verified_at
            """,
            (
                record["approval_id"],
                record["status"],
                record["action"],
                record["target"],
                record.get(
                    "expected_state"
                ),
                record.get(
                    "observed_state"
                ),
                record.get(
                    "detail",
                    ""
                ),
                str(
                    record.get(
                        "evidence",
                        []
                    )
                ),
                record["verified_at"],
            )
        )


        cursor.execute(
            """
            UPDATE action_requests

            SET status=?

            WHERE id=?
            """,
            (
                action_status,
                record[
                    "approval_id"
                ],
            )
        )


        self.conn.commit()


        return {
            "approval_id":
                record[
                    "approval_id"
                ],

            "status":
                action_status,

            "verification":
                record[
                    "status"
                ],
        }


    @serialized_connection
    def get_action_verification(
        self,
        approval_id,
    ):

        import ast

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT
                approval_id,
                status,
                action,
                target,
                expected_state,
                observed_state,
                detail,
                evidence,
                verified_at

            FROM action_verifications

            WHERE approval_id=?
            """,
            (
                approval_id,
            )
        )

        row = cursor.fetchone()

        if not row:
            return None


        evidence = []

        if row[7]:

            try:
                evidence = ast.literal_eval(
                    row[7]
                )

            except Exception:
                evidence = [
                    str(
                        row[7]
                    )
                ]


        return {
            "approval_id":
                row[0],

            "status":
                row[1],

            "action":
                row[2],

            "target":
                row[3],

            "expected_state":
                row[4],

            "observed_state":
                row[5],

            "detail":
                row[6],

            "evidence":
                evidence,

            "verified_at":
                row[8],
        }


    @serialized_connection
    def get_action_verification_history(
        self,
        approval_id,
    ):

        import ast

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                approval_id,
                status,
                action,
                target,
                expected_state,
                observed_state,
                detail,
                evidence,
                verified_at,
                source,
                requested_by

            FROM action_verification_history

            WHERE approval_id=?

            ORDER BY id ASC
            """,
            (
                approval_id,
            )
        )

        records = []

        for row in cursor.fetchall():

            evidence = []

            if row[8]:

                try:
                    evidence = ast.literal_eval(
                        row[8]
                    )

                except Exception:
                    evidence = [
                        str(
                            row[8]
                        )
                    ]

            records.append(
                {
                    "id":
                        row[0],

                    "approval_id":
                        row[1],

                    "status":
                        row[2],

                    "action":
                        row[3],

                    "target":
                        row[4],

                    "expected_state":
                        row[5],

                    "observed_state":
                        row[6],

                    "detail":
                        row[7],

                    "evidence":
                        evidence,

                    "verified_at":
                        row[9],

                    "source":
                        row[10],

                    "requested_by":
                        row[11],
                }
            )

        return records


    @serialized_connection
    def save_action_history(
        self,
        execution,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT INTO action_history (

                id,
                approval_id,
                action,
                target,
                status,
                result,
                executed_at,
                evidence

            )

            VALUES (?,?,?,?,?,?,?,?)

            """,
            (

                execution["id"],

                execution["approval_id"],

                execution["action"],

                execution["target"],

                execution["status"],

                execution["result"],

                execution["executed_at"],

                str(
                    execution.get(
                        "evidence",
                        []
                    )
                ),

            )
        )

        self.conn.commit()



    def save_learning(
        self,
        record,
    ):

        cursor = self.conn.cursor()


        cursor.execute(
            """
            INSERT INTO learning_records (

                incident_id,

                action,

                result,

                resolution,

                confidence,

                created_at,

                evidence

            )

            VALUES (?,?,?,?,?,?,?)

            """,
            (

                record.incident_id,

                record.action,

                record.result,

                record.resolution,

                record.confidence,

                datetime.now(UTC).isoformat(),

                str(
                    record.evidence
                ),

            )
        )


        self.conn.commit()





    def get_learning_records(
        self,
    ):

        cursor = self.conn.cursor()


        cursor.execute(
            """
            SELECT

                id,

                incident_id,

                action,

                result,

                resolution,

                confidence,

                created_at,

                evidence


            FROM learning_records


            ORDER BY created_at DESC


            """
        )


        return cursor.fetchall()






    @serialized_connection
    def get_action_history(
        self,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT

                id,
                approval_id,
                action,
                target,
                status,
                result,
                executed_at

            FROM action_history

            ORDER BY executed_at DESC

            """
        )


        return cursor.fetchall()
