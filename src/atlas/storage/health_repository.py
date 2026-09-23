from datetime import datetime, UTC

from atlas.storage.database import Database



class HealthFindingRepository:


    def __init__(self):

        self.database = Database()



    def save(
        self,
        finding,
    ):

        #
        # INFO observations are evidence only.
        # They must not create health findings.
        #
        if finding.severity == "INFO":
            return


        cursor = self.database.conn.cursor()


        finding_key = finding.key()



        cursor.execute(
            """
            SELECT
                id,
                occurrences

            FROM health_findings

            WHERE finding_key = ?

            """,
            (
                finding_key,
            )
        )


        existing = cursor.fetchone()



        now = datetime.now(UTC).isoformat()



        if existing:


            cursor.execute(
                """
                UPDATE health_findings

                SET

                    occurrences = occurrences + 1,

                    last_seen = ?,

                    severity = ?,

                    message = ?,

                    status = 'active'

                WHERE id = ?

                """,
                (
                    now,
                    finding.severity,
                    finding.message,
                    existing[0],
                )
            )


        else:


            cursor.execute(
                """
                INSERT INTO health_findings
                (
                    asset_id,
                    finding_key,
                    severity,
                    title,
                    message,
                    category,
                    status,
                    occurrences,
                    created_at,
                    last_seen
                )

                VALUES
                (?,?,?,?,?,?,?,?,?,?)

                """,
                (
                    finding.asset_id,
                    finding_key,
                    finding.severity,
                    finding.title,
                    finding.message,
                    finding.category,
                    "active",
                    1,
                    now,
                    now,
                )
            )



        self.database.conn.commit()



    def get_active(
        self,
    ):

        cursor = self.database.conn.cursor()



        cursor.execute(
            """
            SELECT

                id,

                asset_id,

                severity,

                title,

                message,

                category,

                status,

                occurrences,

                created_at,

                last_seen


            FROM health_findings


            WHERE status = 'active'


            ORDER BY last_seen DESC

            """
        )


        rows = cursor.fetchall()



        return [

            {
                "id": row[0],
                "asset_id": row[1],
                "severity": row[2],
                "title": row[3],
                "message": row[4],
                "category": row[5],
                "status": row[6],
                "occurrences": row[7],
                "created_at": row[8],
                "last_seen": row[9],
            }

            for row in rows

        ]
