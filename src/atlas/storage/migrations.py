import sqlite3


def migrate(connection: sqlite3.Connection):

    cursor = connection.cursor()


    #
    # events.event_key
    #

    cursor.execute(
        """
        PRAGMA table_info(events)
        """
    )

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    if "event_key" not in columns:

        cursor.execute(
            """
            ALTER TABLE events
            ADD COLUMN event_key TEXT
            """
        )


    #
    # events.severity
    #

    cursor.execute(
        """
        PRAGMA table_info(events)
        """
    )

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    if "severity" not in columns:

        cursor.execute(
            """
            ALTER TABLE events
            ADD COLUMN severity TEXT DEFAULT 'warning'
            """
        )


    #
    # events.category
    #

    cursor.execute(
        """
        PRAGMA table_info(events)
        """
    )

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    if "category" not in columns:

        cursor.execute(
            """
            ALTER TABLE events
            ADD COLUMN category TEXT DEFAULT 'system'
            """
        )


    #
    # events.occurrences
    #

    cursor.execute(
        """
        PRAGMA table_info(events)
        """
    )

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    if "occurrences" not in columns:

        cursor.execute(
            """
            ALTER TABLE events
            ADD COLUMN occurrences INTEGER DEFAULT 1
            """
        )


    #
    # assets.identity_json
    #

    cursor.execute(
        """
        PRAGMA table_info(assets)
        """
    )

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    if "identity_json" not in columns:

        cursor.execute(
            """
            ALTER TABLE assets
            ADD COLUMN identity_json TEXT
            """
        )


    #
    # asset_history table
    #

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS asset_history (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            asset_id TEXT NOT NULL,

            health REAL NOT NULL,

            status TEXT NOT NULL,

            snapshot_at TEXT NOT NULL

        )
        """
    )


    #
    # asset_relationships table
    #

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS asset_relationships (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            source_asset_id TEXT NOT NULL,

            target_asset_id TEXT NOT NULL,

            relationship_type TEXT NOT NULL,

            metadata_json TEXT,

            created_at TEXT NOT NULL,

            status TEXT DEFAULT 'ACTIVE',

            first_seen TEXT,

            last_seen TEXT

        )
        """
    )


    #
    # asset_relationship lifecycle migration
    #

    cursor.execute(
        """
        PRAGMA table_info(asset_relationships)
        """
    )

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]


    if "status" not in columns:

        cursor.execute(
            """
            ALTER TABLE asset_relationships
            ADD COLUMN status TEXT DEFAULT 'ACTIVE'
            """
        )


    if "first_seen" not in columns:

        cursor.execute(
            """
            ALTER TABLE asset_relationships
            ADD COLUMN first_seen TEXT
            """
        )


    if "last_seen" not in columns:

        cursor.execute(
            """
            ALTER TABLE asset_relationships
            ADD COLUMN last_seen TEXT
            """
        )


    #
    # relationship intelligence migration
    #

    cursor.execute(
        """
        PRAGMA table_info(asset_relationships)
        """
    )

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]


    if "confidence" not in columns:

        cursor.execute(
            """
            ALTER TABLE asset_relationships
            ADD COLUMN confidence REAL DEFAULT 1.0
            """
        )


    if "evidence_json" not in columns:

        cursor.execute(
            """
            ALTER TABLE asset_relationships
            ADD COLUMN evidence_json TEXT
            """
        )


    #
    # Prevent duplicate relationships
    #

    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_asset_relationship_unique

        ON asset_relationships
        (
            source_asset_id,
            target_asset_id,
            relationship_type
        )
        """
    )


    #
    # asset_capabilities
    #

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS asset_capabilities(

            asset_id TEXT NOT NULL,

            capability TEXT NOT NULL,

            PRIMARY KEY(asset_id, capability)

        )
        '''
    )


    #
    # asset_roles
    #

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS asset_roles(

            asset_id TEXT NOT NULL,

            role TEXT NOT NULL,

            PRIMARY KEY(asset_id, role)

        )
        '''
    )


    #
    # asset_metadata
    #

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS asset_metadata(

            asset_id TEXT NOT NULL,

            key TEXT NOT NULL,

            value TEXT,

            PRIMARY KEY(asset_id, key)

        )
        '''
    )



    #
    # Asset role intelligence persistence
    #
    cursor.execute(
        """
        PRAGMA table_info(assets)
        """
    )

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    if "service_role" not in columns:
        cursor.execute(
            """
            ALTER TABLE assets
            ADD COLUMN service_role TEXT DEFAULT 'UNKNOWN'
            """
        )

    if "service_importance" not in columns:
        cursor.execute(
            """
            ALTER TABLE assets
            ADD COLUMN service_importance TEXT DEFAULT 'SYSTEM'
            """
        )

    if "primary_role" not in columns:
        cursor.execute(
            """
            ALTER TABLE assets
            ADD COLUMN primary_role TEXT DEFAULT 'UNKNOWN'
            """
        )

    if "role_confidence" not in columns:
        cursor.execute(
            """
            ALTER TABLE assets
            ADD COLUMN role_confidence INTEGER DEFAULT 0
            """
        )

    if "role_evidence_json" not in columns:
        cursor.execute(
            """
            ALTER TABLE assets
            ADD COLUMN role_evidence_json TEXT
            """
        )


    #
    # Asset inventory presence lifecycle.
    #
    # Operational status (ONLINE/OFFLINE/DEGRADED) and inventory
    # presence (ACTIVE/STALE/RETIRED) are separate concepts.
    #
    cursor.execute(
        """
        PRAGMA table_info(assets)
        """
    )

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    if "presence" not in columns:

        cursor.execute(
            """
            ALTER TABLE assets
            ADD COLUMN presence TEXT NOT NULL DEFAULT 'ACTIVE'
            """
        )

    if "presence_changed_at" not in columns:

        cursor.execute(
            """
            ALTER TABLE assets
            ADD COLUMN presence_changed_at TEXT
            """
        )

    #
    # Existing rows existed before the presence lifecycle. Their
    # last_seen timestamp is the best historical baseline.
    #
    cursor.execute(
        """
        UPDATE assets
        SET presence_changed_at = last_seen
        WHERE presence_changed_at IS NULL
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
            idx_assets_presence
        ON assets(
            presence
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS asset_presence_events (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            asset_id TEXT NOT NULL,

            from_presence TEXT NOT NULL,

            to_presence TEXT NOT NULL,

            reason TEXT NOT NULL,

            timestamp TEXT NOT NULL

        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
            idx_asset_presence_events_asset
        ON asset_presence_events(
            asset_id,
            id
        )
        """
    )


    connection.commit()


    #
    # incidents timeline
    #

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS incident_events (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            incident_id TEXT NOT NULL,

            timestamp TEXT NOT NULL,

            type TEXT NOT NULL,

            detail TEXT,

            severity TEXT,

            impact TEXT

        )
        """
    )

