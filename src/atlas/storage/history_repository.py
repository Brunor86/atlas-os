from atlas.storage.database import Database
from atlas.core.history import AssetHistory

from datetime import datetime


class HistoryRepository:

    def __init__(self):

        self.database = Database()


    def save(
        self,
        history: AssetHistory,
    ):

        cursor = self.database.conn.cursor()

        cursor.execute(
            """
            INSERT INTO asset_history
            (
                asset_id,
                health,
                status,
                snapshot_at
            )

            VALUES
            (?,?,?,?)
            """,
            (
                history.asset_id,
                history.health,
                history.status,
                history.snapshot_at.isoformat(),
            ),
        )

        self.database.conn.commit()


    def get_history(
        self,
        asset_id,
        limit=100,
    ):

        cursor = self.database.conn.cursor()

        cursor.execute(
            """
            SELECT

                asset_id,

                health,

                status,

                snapshot_at

            FROM asset_history

            WHERE asset_id = ?

            ORDER BY snapshot_at DESC

            LIMIT ?

            """,
            (
                asset_id,
                limit,
            ),
        )

        rows = cursor.fetchall()

        history = []

        for row in rows:

            history.append(

                AssetHistory(

                    asset_id=row[0],

                    health=row[1],

                    status=row[2],

                    snapshot_at=datetime.fromisoformat(
                        row[3]
                    ),

                )

            )

        return history
