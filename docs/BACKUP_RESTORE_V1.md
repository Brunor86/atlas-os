# ATLAS OS v1.0 Backup and Restore

## Production database

Default path:

    /opt/atlas/atlas.db

ATLAS uses SQLite and may operate in WAL mode.

A simple copy of `atlas.db` while writers are active is not considered a
guaranteed consistent backup because committed data may still reside in WAL.

## Online backup

Use SQLite's backup API.

Example:

    import sqlite3

    source = "/opt/atlas/atlas.db"
    target = "/opt/atlas-backups/atlas.db"

    src = sqlite3.connect(
        "file:" + source + "?mode=ro",
        uri=True,
    )

    dst = sqlite3.connect(target)

    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

Every backup must then pass:

    PRAGMA integrity_check

Expected result:

    ok

## Release backup evidence

A release backup should record:

- verified SQLite database;
- Git commit SHA;
- release/tag name;
- timestamp;
- deployment configuration backup when deployment configuration changed.

Authentication tokens must never be stored in repository documentation or
release artifacts.

## Restore prerequisites

Before restore:

1. identify the exact backup;
2. verify backup integrity;
3. ensure no Operator action is executing;
4. prevent new operational approvals;
5. stop ATLAS writers;
6. preserve the current DB before replacement.

Main writers:

    atlas-collector.service
    atlas-web.service

## Controlled restore outline

Stop services:

    systemctl stop atlas-collector.service
    systemctl stop atlas-web.service

Confirm they are stopped before replacing state.

Preserve the current database.

Restore the verified backup through a temporary path.

Then verify the temporary restored database before moving it into the
production path.

Conceptual sequence:

    verified backup
      -> temporary restored DB
      -> integrity_check
      -> replace production atlas.db
      -> clear obsolete WAL/SHM only with all writers stopped
      -> restore ownership/mode
      -> start services
      -> HTTP/API checks
      -> final integrity_check

## Post-restore acceptance

Required:

- integrity_check = ok;
- atlas-collector active;
- atlas-web active;
- /api/assets responds;
- /api/incidents responds;
- /api/ai/status responds;
- latest snapshot can be loaded;
- Operator history remains readable;
- no unexpected systemd warnings.

## Execution claims are safety state

`action_execution_claims` must be preserved.

Never delete execution claims merely to retry an uncertain operation.

An existing claim may represent a remote operation whose outcome is not yet
known.

Inspect the real target and action history first.

If another mutation is necessary, create a new proposal and obtain a new
approval.

## Code rollback is not DB rollback

Rolling application code back and restoring the database are separate
decisions.

Do not automatically restore the DB merely because Git code is rolled back.

Older ATLAS code that does not understand current safety tables must not be
allowed to execute governed actions.

## Recovery objective

A successful recovery preserves:

- DB integrity;
- audit history;
- approval safety;
- execution claims;
- verification evidence;
- known infrastructure state.
