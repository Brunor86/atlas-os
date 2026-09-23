import json

from atlas.storage.database import Database


class GraphRepository:

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
                created_at,
                confidence,
                evidence_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                relationship.source,
                relationship.target,
                relationship.type.name,
                json.dumps(relationship.metadata or {}),
                relationship.created_at.isoformat(),
                float(relationship.confidence),
                json.dumps(relationship.evidence or []),
            ),
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

    def get_parents(self, asset_id):
        cursor = self.database.conn.cursor()

        cursor.execute(
            """
            SELECT
                source_asset_id,
                target_asset_id,
                relationship_type,
                metadata_json,
                created_at,
                confidence,
                evidence_json
            FROM asset_relationships
            WHERE target_asset_id = ?
            ORDER BY id DESC
            """,
            (asset_id,),
        )

        rows = cursor.fetchall()

        return [
            {
                "source": row[0],
                "target": row[1],
                "type": row[2],
                "metadata": json.loads(row[3]) if row[3] else {},
                "created_at": row[4],
                "confidence": row[5],
                "evidence": json.loads(row[6]) if row[6] else [],
            }
            for row in rows
        ]

    def get_children(self, asset_id):
        cursor = self.database.conn.cursor()

        cursor.execute(
            """
            SELECT
                source_asset_id,
                target_asset_id,
                relationship_type,
                metadata_json,
                created_at,
                confidence,
                evidence_json
            FROM asset_relationships
            WHERE source_asset_id = ?
            ORDER BY id DESC
            """,
            (asset_id,),
        )

        rows = cursor.fetchall()

        return [
            {
                "source": row[0],
                "target": row[1],
                "type": row[2],
                "metadata": json.loads(row[3]) if row[3] else {},
                "created_at": row[4],
                "confidence": row[5],
                "evidence": json.loads(row[6]) if row[6] else [],
            }
            for row in rows
        ]

    def get_neighbors(self, asset_id):
        return (
            self.get_parents(asset_id)
            + self.get_children(asset_id)
        )

    def exists_relationship(
        self,
        source,
        target,
        relationship_type,
    ):
        cursor = self.database.conn.cursor()

        cursor.execute(
            """
            SELECT 1
            FROM asset_relationships
            WHERE source_asset_id = ?
              AND target_asset_id = ?
              AND relationship_type = ?
            LIMIT 1
            """,
            (
                source,
                target,
                relationship_type,
            ),
        )

        return cursor.fetchone() is not None

    def get_impact_tree(
        self,
        asset_id,
        max_depth=3,
    ):
        """
        Return the operational impact tree.

        Includes both:
        - downstream dependents
        - upstream supporting infrastructure

        This allows an application failure such as:

            NPM -> Debian VM -> Proxmox Host

        to be represented as operational impact even when the
        failed application has no downstream children.
        """

        visited = set()
        result = []

        def add_item(
            target,
            relationship,
            direction,
            depth,
            confidence,
            evidence,
        ):
            if target == asset_id:
                return

            result.append(
                {
                    "asset_id": target,
                    "relationship": relationship,
                    "direction": direction,
                    "depth": depth,
                    "confidence": confidence,
                    "evidence": evidence,
                }
            )

        def walk_downstream(current, depth):
            if depth > max_depth:
                return

            key = ("DOWNSTREAM", current)

            if key in visited:
                return

            visited.add(key)

            for child in self.get_children(current):
                target = child["target"]

                add_item(
                    target,
                    child["type"],
                    "DOWNSTREAM",
                    depth,
                    child["confidence"],
                    child["evidence"],
                )

                walk_downstream(
                    target,
                    depth + 1,
                )

        def walk_upstream(current, depth):
            if depth > max_depth:
                return

            key = ("UPSTREAM", current)

            if key in visited:
                return

            visited.add(key)

            for parent in self.get_parents(current):
                source = parent["source"]

                add_item(
                    source,
                    parent["type"],
                    "UPSTREAM",
                    depth,
                    parent["confidence"],
                    parent["evidence"],
                )

                walk_upstream(
                    source,
                    depth + 1,
                )

        # Start both directions from the failed asset.
        walk_downstream(
            asset_id,
            1,
        )

        walk_upstream(
            asset_id,
            1,
        )

        # Deduplicate the same asset while preserving the strongest
        # available representation.
        deduplicated = {}

        for item in result:
            key = (
                item["asset_id"],
                item["direction"],
            )

            existing = deduplicated.get(key)

            if existing is None:
                deduplicated[key] = item
                continue

            if (
                float(item.get("confidence", 0.0) or 0.0)
                > float(existing.get("confidence", 0.0) or 0.0)
            ):
                deduplicated[key] = item

        return list(
            deduplicated.values()
        )

    def get_upstream_impact_tree(
        self,
        asset_id,
        max_depth=3,
    ):
        visited = set()
        result = []

        def walk(current, depth):
            if depth > max_depth:
                return

            if current in visited:
                return

            visited.add(current)

            parents = self.get_parents(current)

            for parent in parents:
                source = parent["source"]

                result.append(
                    {
                        "asset_id": source,
                        "relationship": parent["type"],
                        "direction": "UPSTREAM",
                        "depth": depth,
                        "confidence": parent["confidence"],
                        "evidence": parent["evidence"],
                    }
                )

                walk(source, depth + 1)

        walk(asset_id, 1)

        return result

    def get_critical_upstream(self, asset_id):
        visited = set()
        result = []

        def walk(current):
            if current in visited:
                return

            visited.add(current)

            parents = self.get_parents(current)

            for parent in parents:
                source = parent["source"]

                result.append(
                    {
                        "asset_id": source,
                        "relationship": parent["type"],
                        "direction": "UPSTREAM",
                        "confidence": parent["confidence"],
                        "evidence": parent["evidence"],
                    }
                )

                walk(source)

        walk(asset_id)

        return result

    def get_operational_upstream(
        self,
        asset_id,
        max_depth=5,
    ):
        """
        Return operationally relevant upstream assets.

        Traversal follows parent relationships while preserving
        traversal depth and relationship metadata.
        """

        visited = set()
        result = []

        def walk(current, depth):
            if depth > max_depth:
                return

            if current in visited:
                return

            visited.add(current)

            parents = self.get_parents(current)

            for parent in parents:
                source = parent["source"]

                if source in visited:
                    continue

                result.append(
                    {
                        "asset_id": source,
                        "relationship": parent["type"],
                        "direction": "UPSTREAM",
                        "depth": depth,
                        "confidence": float(
                            parent.get(
                                "confidence",
                                1.0,
                            )
                            or 0.0
                        ),
                        "evidence": list(
                            parent.get(
                                "evidence",
                                [],
                            )
                            or []
                        ),
                        "relationship_weight": parent.get(
                            "weight",
                            parent.get(
                                "relationship_weight",
                                0,
                            ),
                        ),
                    }
                )

                walk(
                    source,
                    depth + 1,
                )

        walk(
            asset_id,
            1,
        )

        return result
