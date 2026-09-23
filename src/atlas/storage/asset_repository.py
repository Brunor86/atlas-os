from atlas.storage.database import Database
from datetime import datetime, UTC
import json

from atlas.core.asset import (
    Asset,
    AssetType,
    AssetStatus,
    AssetPresence,
    Criticality,
    Capability,
    AssetRole,
    ServiceRole,
    ServiceImportance,
)

from atlas.core.relationship import (
    Relationship,
    RelationshipType,
)

from atlas.core.identity import AssetIdentity
from atlas.core.observation import Observation



class AssetRepository:


    def __init__(self):

        self.database = Database()



    def save_asset(self, asset):

        cursor = self.database.conn.cursor()

        identity_json = json.dumps(
            {
                "serial": asset.identity.serial,
                "model": asset.identity.model,
                "vendor": asset.identity.vendor,
                "firmware": asset.identity.firmware,
                "device": asset.identity.device,
            }
        )

        presence_changed_at = (
            asset.presence_changed_at
            or datetime.now(UTC)
        )

        cursor.execute(
            """
            INSERT INTO assets
            (
                id,
                name,
                type,
                status,
                health,
                criticality,
                last_seen,
                identity_json,
                service_role,
                service_importance,
                primary_role,
                role_confidence,
                role_evidence_json,
                presence,
                presence_changed_at
            )
            VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET

                name = excluded.name,
                type = excluded.type,
                status = excluded.status,
                health = excluded.health,
                criticality = excluded.criticality,
                last_seen = excluded.last_seen,
                identity_json = excluded.identity_json,
                service_role = excluded.service_role,
                service_importance = excluded.service_importance,
                primary_role = excluded.primary_role,
                role_confidence = excluded.role_confidence,
                role_evidence_json = excluded.role_evidence_json

            """,
            (
                asset.id,
                asset.name,
                asset.type.name,
                asset.status.name,
                asset.health,
                asset.criticality.name,
                asset.last_seen.isoformat(),
                identity_json,
                asset.service_role.name,
                asset.service_importance.name,
                asset.primary_role.name,
                asset.role_confidence,
                json.dumps(asset.role_evidence),
                asset.presence.name,
                presence_changed_at.isoformat(),
            )
        )

        #
        # Capabilities
        #

        cursor.execute(
            "DELETE FROM asset_capabilities WHERE asset_id=?",
            (asset.id,)
        )

        for capability in asset.capabilities:

            cursor.execute(
                """
                INSERT INTO asset_capabilities
                (
                    asset_id,
                    capability
                )
                VALUES
                (?,?)
                """,
                (
                    asset.id,
                    capability.name,
                )
            )

        #
        # Roles
        #

        cursor.execute(
            "DELETE FROM asset_roles WHERE asset_id=?",
            (asset.id,)
        )

        for role in asset.asset_roles:

            cursor.execute(
                """
                INSERT INTO asset_roles
                (
                    asset_id,
                    role
                )
                VALUES
                (?,?)
                """,
                (
                    asset.id,
                    role.name,
                )
            )

        #
        # Metadata
        #

        cursor.execute(
            "DELETE FROM asset_metadata WHERE asset_id=?",
            (asset.id,)
        )

        for key, value in asset.metadata.items():

            cursor.execute(
                """
                INSERT INTO asset_metadata
                (
                    asset_id,
                    key,
                    value
                )
                VALUES
                (?,?,?)
                """,
                (
                    asset.id,
                    key,
                    json.dumps(value, default=str),
                )
            )

        self.database.conn.commit()



    def save_observation(self, observation):

        cursor = self.database.conn.cursor()


        cursor.execute(
            """
            INSERT OR IGNORE INTO observations
            (
                asset_id,
                type,
                value,
                severity,
                source,
                timestamp
            )
            VALUES
            (?,?,?,?,?,?)
            """,
            (
                observation.asset_id,
                observation.type,
                json.dumps(
                    observation.value,
                    default=str,
                    sort_keys=True,
                ),
                observation.severity,
                observation.source,
                observation.timestamp.isoformat(),
            )
        )


        self.database.conn.commit()




    def find_by_identity(self, identity):

        if not identity:
            return None

        # An empty identity is not useful for matching.
        if not any(
            (
                identity.vendor,
                identity.model,
                identity.serial,
                identity.firmware,
                identity.device,
            )
        ):
            return None

        cursor = self.database.conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                identity_json,
                presence

            FROM assets

            ORDER BY
                CASE presence
                    WHEN 'ACTIVE' THEN 0
                    WHEN 'STALE' THEN 1
                    WHEN 'RETIRED' THEN 2
                    ELSE 3
                END,
                id
            """
        )

        rows = cursor.fetchall()

        for row in rows:

            data = json.loads(
                row[1] or "{}"
            )

            if (
                data.get("vendor") == identity.vendor
                and data.get("model") == identity.model
                and data.get("serial") == identity.serial
                and data.get("firmware") == identity.firmware
                and data.get("device") == identity.device
            ):
                return row[0]

        return None


    def get_asset(self, asset_id):

        cursor = self.database.conn.cursor()


        cursor.execute(
            """
            SELECT
                id,
                name,
                type,
                status,
                health,
                criticality,
                last_seen,
                identity_json,
                service_role,
                service_importance,
                primary_role,
                role_confidence,
                role_evidence_json,
                presence,
                presence_changed_at

            FROM assets

            WHERE id = ?
            """,
            (
                asset_id,
            )
        )


        row = cursor.fetchone()


        if not row:

            return None


        asset = self._row_to_asset(row)

        self._load_metadata(asset)
        self._load_capabilities(asset)
        self._load_roles(asset)
        self._load_relationships(asset)
        self._load_observations(asset)

        return asset



    def _load_capabilities(self, asset):

        cursor = self.database.conn.cursor()

        cursor.execute(
            "SELECT capability FROM asset_capabilities WHERE asset_id=?",
            (asset.id,)
        )

        for (cap,) in cursor.fetchall():
            asset.capabilities.add(
                Capability[cap]
            )


    def _load_roles(self, asset):

        cursor = self.database.conn.cursor()

        cursor.execute(
            "SELECT role FROM asset_roles WHERE asset_id=?",
            (asset.id,)
        )

        for (role,) in cursor.fetchall():
            asset.asset_roles.add(
                AssetRole[role]
            )


    def _load_metadata(self, asset):

        cursor = self.database.conn.cursor()

        cursor.execute(
            "SELECT key,value FROM asset_metadata WHERE asset_id=?",
            (asset.id,)
        )

        asset.metadata = {}

        for key, value in cursor.fetchall():

            try:
                asset.metadata[key] = json.loads(value)
            except (TypeError, json.JSONDecodeError):
                # Backward compatibility with metadata persisted
                # by older ATLAS versions.
                asset.metadata[key] = value


    def _load_relationships(self, asset):

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
            WHERE source_asset_id=?
            """,
            (asset.id,)
        )

        import json
        from datetime import datetime

        for row in cursor.fetchall():

            asset.relationships.append(

                Relationship(

                    source=row[0],

                    target=row[1],

                    type=RelationshipType[row[2]],

                    metadata=json.loads(
                        row[3] or "{}"
                    ),

                    created_at=datetime.fromisoformat(
                        row[4]
                    ),

                )

            )



    def get_all_assets(self):

        cursor = self.database.conn.cursor()


        cursor.execute(
            """
            SELECT
                id,
                name,
                type,
                status,
                health,
                criticality,
                last_seen,
                identity_json,
                service_role,
                service_importance,
                primary_role,
                role_confidence,
                role_evidence_json,
                presence,
                presence_changed_at

            FROM assets

            ORDER BY name
            """
        )


        rows = cursor.fetchall()


        assets = []


        for row in rows:

            asset = self._row_to_asset(row)

            self._load_metadata(asset)
            self._load_capabilities(asset)
            self._load_roles(asset)
            self._load_relationships(asset)
            # observations loaded on demand

            assets.append(asset)


        return assets



    def get_observations(self, asset_id):

        cursor = self.database.conn.cursor()


        cursor.execute(
            """
            SELECT
                type,
                value,
                severity,
                source,
                timestamp

            FROM observations

            WHERE asset_id = ?

            ORDER BY id ASC
            LIMIT 100
            """,
            (
                asset_id,
            )
        )


        rows = cursor.fetchall()


        observations = []

        for row in rows:

            value = row[1]

            try:
                value = json.loads(
                    value
                )
            except (
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ):
                pass

            timestamp = None

            if row[4]:

                try:
                    from datetime import datetime

                    timestamp = datetime.fromisoformat(
                        row[4]
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    timestamp = None

            observation = Observation(
                asset_id=asset_id,
                type=row[0],
                value=value,
                severity=row[2],
                source=row[3],
            )

            if timestamp is not None:
                observation.timestamp = timestamp

            observations.append(
                observation
            )

        return observations



    def _load_observations(self, asset):

        observations = self.get_observations(
            asset.id
        )


        for observation in observations:

            asset.add_observation(
                observation
            )



    def get_assets_by_type(self, asset_type):

        cursor = self.database.conn.cursor()


        cursor.execute(
            """
            SELECT
                id,
                name,
                type,
                status,
                health,
                criticality,
                last_seen,
                identity_json,
                service_role,
                service_importance,
                primary_role,
                role_confidence,
                role_evidence_json,
                presence,
                presence_changed_at

            FROM assets

            WHERE type = ?

            """,
            (
                asset_type,
            )
        )


        rows = cursor.fetchall()


        assets = []


        for row in rows:

            asset = self._row_to_asset(row)

            self._load_metadata(asset)
            self._load_capabilities(asset)
            self._load_roles(asset)
            self._load_relationships(asset)
            # observations loaded on demand

            assets.append(asset)


        return assets



    def get_unhealthy_assets(self):

        cursor = self.database.conn.cursor()


        cursor.execute(
            """
            SELECT
                id,
                name,
                type,
                status,
                health,
                criticality,
                last_seen,
                identity_json,
                service_role,
                service_importance,
                primary_role,
                role_confidence,
                role_evidence_json,
                presence,
                presence_changed_at

            FROM assets

            WHERE health < 80

            ORDER BY health ASC
            """
        )


        rows = cursor.fetchall()


        assets = []


        for row in rows:

            asset = self._row_to_asset(row)

            self._load_metadata(asset)
            self._load_capabilities(asset)
            self._load_roles(asset)
            self._load_relationships(asset)
            # observations loaded on demand

            assets.append(asset)


        return assets



    def get_operational_assets(self):

        return [
            asset
            for asset
            in self.get_all_assets()
            if (
                asset.presence
                != AssetPresence.RETIRED
            )
        ]


    def get_active_assets(self):

        return [
            asset
            for asset
            in self.get_all_assets()
            if (
                asset.presence
                == AssetPresence.ACTIVE
            )
        ]


    def set_presence(
        self,
        asset_id,
        presence,
        *,
        reason,
        changed_at=None,
    ):

        if not isinstance(
            presence,
            AssetPresence,
        ):
            presence = (
                AssetPresence[
                    str(presence)
                ]
            )

        changed_at = (
            changed_at
            or datetime.now(UTC)
        )

        cursor = (
            self.database.conn.cursor()
        )

        cursor.execute(
            """
            SELECT presence
            FROM assets
            WHERE id = ?
            """,
            (
                asset_id,
            )
        )

        row = cursor.fetchone()

        if not row:
            return False

        previous = (
            row[0]
            or AssetPresence.ACTIVE.name
        )

        if (
            previous
            == presence.name
        ):
            return False

        cursor.execute(
            """
            UPDATE assets
            SET
                presence = ?,
                presence_changed_at = ?
            WHERE id = ?
            """,
            (
                presence.name,
                changed_at.isoformat(),
                asset_id,
            )
        )

        cursor.execute(
            """
            INSERT INTO asset_presence_events
            (
                asset_id,
                from_presence,
                to_presence,
                reason,
                timestamp
            )
            VALUES
            (?,?,?,?,?)
            """,
            (
                asset_id,
                previous,
                presence.name,
                reason,
                changed_at.isoformat(),
            )
        )

        self.database.conn.commit()

        return True


    def get_presence_events(
        self,
        asset_id=None,
    ):

        cursor = (
            self.database.conn.cursor()
        )

        if asset_id is None:

            cursor.execute(
                """
                SELECT
                    asset_id,
                    from_presence,
                    to_presence,
                    reason,
                    timestamp
                FROM asset_presence_events
                ORDER BY id ASC
                """
            )

        else:

            cursor.execute(
                """
                SELECT
                    asset_id,
                    from_presence,
                    to_presence,
                    reason,
                    timestamp
                FROM asset_presence_events
                WHERE asset_id = ?
                ORDER BY id ASC
                """,
                (
                    asset_id,
                )
            )

        return [
            {
                "asset_id": row[0],
                "from_presence": row[1],
                "to_presence": row[2],
                "reason": row[3],
                "timestamp": row[4],
            }
            for row
            in cursor.fetchall()
        ]


    def _row_to_asset(self, row):

        identity_data = {}

        if row[7]:
            identity_data = json.loads(row[7])

        service_role = (
            ServiceRole[row[8]]
            if len(row) > 8 and row[8]
            else ServiceRole.UNKNOWN
        )

        service_importance = (
            ServiceImportance[row[9]]
            if len(row) > 9 and row[9]
            else ServiceImportance.SYSTEM
        )

        primary_role = (
            AssetRole[row[10]]
            if len(row) > 10 and row[10]
            else AssetRole.UNKNOWN
        )

        role_confidence = (
            int(row[11])
            if len(row) > 11 and row[11] is not None
            else 0
        )

        role_evidence = []

        if len(row) > 12 and row[12]:
            role_evidence = json.loads(row[12])

        presence = (
            AssetPresence[row[13]]
            if len(row) > 13 and row[13]
            else AssetPresence.ACTIVE
        )

        presence_changed_at = None

        if (
            len(row) > 14
            and row[14]
        ):

            presence_changed_at = (
                datetime.fromisoformat(
                    row[14]
                )
            )

        return Asset(

            id=row[0],

            name=row[1],

            type=AssetType[row[2]],

            status=AssetStatus[row[3]],

            health=row[4],

            criticality=Criticality[row[5]],

            last_seen=datetime.fromisoformat(
                row[6]
            ),

            identity=AssetIdentity(
                serial=identity_data.get("serial"),
                model=identity_data.get("model"),
                vendor=identity_data.get("vendor"),
                firmware=identity_data.get("firmware"),
                device=identity_data.get("device"),
            ),

            service_role=service_role,

            service_importance=service_importance,

            primary_role=primary_role,

            role_confidence=role_confidence,

            role_evidence=role_evidence,

            presence=presence,

            presence_changed_at=(
                presence_changed_at
            ),

        )
