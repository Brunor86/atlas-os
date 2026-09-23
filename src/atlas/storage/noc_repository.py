
import json

from datetime import datetime, UTC

from atlas.storage.database import Database


class NOCRepository:


    def __init__(self):

        self.db = Database()


    def save(
        self,
        report,
    ):

        conn = self.db.conn


        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS noc_reports (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                created_at TEXT NOT NULL,

                data TEXT NOT NULL

            )
            """
        )


        conn.execute(
            """
            INSERT INTO noc_reports
            (
                created_at,
                data
            )
            VALUES (?,?)
            """,
            (
                datetime.now(UTC).isoformat(),
                json.dumps(
                    report,
                    default=str,
                ),
            )
        )


        conn.commit()



    def latest(self):

        cursor = self.db.conn.execute(
            """
            SELECT data
            FROM noc_reports
            ORDER BY id DESC
            LIMIT 1
            """
        )


        row = cursor.fetchone()


        if not row:
            return None


        return json.loads(
            row[0]
        )
