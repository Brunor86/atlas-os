import json

from datetime import datetime, UTC

from atlas.storage.database import Database


class RelationshipRepository:


    def __init__(self):

        self.database = Database()



    def save_relationship(self, relationship):

        cursor = self.database.conn.cursor()


        cursor.execute(
            """
            INSERT OR IGNORE INTO asset_relationships
            (
                source_asset_id,
                target_asset_id,
                relationship_type,
                metadata_json,
                created_at
            )

            VALUES
            (?,?,?,?,?)
            """,
            (
                relationship.source,
                relationship.target,
                relationship.type.name,
                json.dumps(
                    relationship.metadata
                ),
                relationship.created_at.isoformat(),
            )
        )


        self.database.conn.commit()



    def get_from_asset(self, asset_id):

        cursor = self.database.conn.cursor()


        cursor.execute(
            """
            SELECT

                source_asset_id,
                target_asset_id,
                relationship_type,
                metadata_json,
                created_at

            FROM asset_relationships

            WHERE source_asset_id = ?

            ORDER BY id DESC

            """,
            (
                asset_id,
            )
        )


        return cursor.fetchall()



    def get_to_asset(self, asset_id):

        cursor = self.database.conn.cursor()


        cursor.execute(
            """
            SELECT

                source_asset_id,
                target_asset_id,
                relationship_type,
                metadata_json,
                created_at

            FROM asset_relationships

            WHERE target_asset_id = ?

            ORDER BY id DESC

            """,
            (
                asset_id,
            )
        )


        return cursor.fetchall()



    def archive_missing_relationships(
        self,
        active_relationships,
    ):

        cursor = self.database.conn.cursor()

        now = datetime.now(UTC).isoformat()

        existing = {
            (
                row[0],
                row[1],
                row[2],
            )
            for row in active_relationships
        }


        cursor.execute(
            """
            SELECT
                source_asset_id,
                target_asset_id,
                relationship_type

            FROM asset_relationships

            WHERE status = 'ACTIVE'
            """
        )


        rows = cursor.fetchall()


        for row in rows:

            key = (
                row[0],
                row[1],
                row[2],
            )


            if key not in existing:

                cursor.execute(
                    """
                    UPDATE asset_relationships

                    SET
                        status = 'REMOVED',
                        last_seen = ?

                    WHERE
                        source_asset_id = ?
                    AND
                        target_asset_id = ?
                    AND
                        relationship_type = ?

                    """,
                    (
                        now,
                        row[0],
                        row[1],
                        row[2],
                    )
                )


        self.database.conn.commit()



    def touch_relationship(
        self,
        relationship,
    ):

        cursor = self.database.conn.cursor()

        now = datetime.now(UTC).isoformat()


        cursor.execute(
            """
            UPDATE asset_relationships

            SET
                status='ACTIVE',
                last_seen=?

            WHERE
                source_asset_id=?
            AND
                target_asset_id=?
            AND
                relationship_type=?

            """,
            (
                now,
                relationship.source,
                relationship.target,
                relationship.type.name,
            )
        )


        if cursor.rowcount == 0:

            cursor.execute(
                """
                INSERT INTO asset_relationships
                (
                    source_asset_id,
                    target_asset_id,
                    relationship_type,
                    metadata_json,
                    created_at,
                    first_seen,
                    last_seen,
                    status
                )

                VALUES
                (?,?,?,?,?,?,?,'ACTIVE')

                """,
                (
                    relationship.source,
                    relationship.target,
                    relationship.type.name,
                    json.dumps(
                        relationship.metadata
                    ),
                    relationship.created_at.isoformat(),
                    now,
                    now,
                )
            )


        self.database.conn.commit()


    def clear_relationships(self):

        cursor = self.database.conn.cursor()

        cursor.execute(
            """
            DELETE FROM asset_relationships
            """
        )

        self.database.conn.commit()
