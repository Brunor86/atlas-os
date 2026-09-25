import json
from datetime import datetime, timezone

from atlas.services.backup_intelligence.inventory import BackupInventoryService


NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)


def service(path):
    return BackupInventoryService(
        manifest_path=path,
        now=lambda: NOW,
    )


def write_manifest(tmp_path, items):
    path = tmp_path / "backup-intelligence.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "items": items,
            }
        )
    )
    return path


def artifact(tmp_path, name, age_hours, checksum=True):
    path = tmp_path / name
    path.write_bytes(b"backup")

    timestamp = NOW.timestamp() - (age_hours * 3600)
    path.touch()
    import os
    os.utime(path, (timestamp, timestamp))

    if checksum:
        sidecar = tmp_path / (name + ".sha256")
        sidecar.write_text("recorded checksum\n")
        os.utime(sidecar, (timestamp, timestamp))

    return path


def test_missing_manifest_is_not_configured(tmp_path):
    result = service(
        tmp_path / "missing.json"
    ).inventory()

    assert result["configured"] is False
    assert result["status"] == "NOT_CONFIGURED"
    assert result["summary"]["total"] == 0


def test_inventory_evaluates_health_staleness_and_exclusion(tmp_path):
    healthy = tmp_path / "healthy"
    stale = tmp_path / "stale"
    healthy.mkdir()
    stale.mkdir()

    artifact(
        healthy,
        "daily-healthy.sql.gz",
        age_hours=6,
    )
    artifact(
        stale,
        "weekly-stale.vma.zst",
        age_hours=200,
    )

    manifest = write_manifest(
        tmp_path,
        [
            {
                "id": "db",
                "name": "Database",
                "asset": "db",
                "kind": "database",
                "policy": "daily",
                "artifact_dir": str(healthy),
                "artifact_pattern": "*.sql.gz",
                "max_age_hours": 30,
                "retention_days": 30,
            },
            {
                "id": "vm",
                "name": "VM",
                "asset": "vm",
                "kind": "guest",
                "policy": "weekly",
                "artifact_dir": str(stale),
                "artifact_pattern": "*.vma.zst",
                "max_age_hours": 180,
            },
            {
                "id": "recreable",
                "name": "Cleanroom",
                "asset": "cleanroom",
                "kind": "guest",
                "policy": "excluded",
                "excluded": True,
                "reason": "recreable",
            },
        ],
    )

    result = service(manifest).inventory()

    states = {
        item["id"]: item["status"]
        for item in result["items"]
    }

    assert result["configured"] is True
    assert result["status"] == "STALE"
    assert result["summary"] == {
        "total": 3,
        "protected": 2,
        "healthy": 1,
        "stale": 1,
        "failed": 0,
        "missing": 0,
        "excluded": 1,
    }
    assert states == {
        "db": "HEALTHY",
        "vm": "STALE",
        "recreable": "EXCLUDED",
    }
    assert result["items"][0]["integrity"] == "RECORDED"


def test_missing_artifact_is_reported(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()

    manifest = write_manifest(
        tmp_path,
        [
            {
                "id": "missing",
                "artifact_dir": str(empty),
                "artifact_pattern": "*.dump",
                "max_age_hours": 30,
            }
        ],
    )

    result = service(manifest).inventory()

    assert result["status"] == "STALE"
    assert result["summary"]["missing"] == 1
    assert result["items"][0]["status"] == "MISSING"


def test_invalid_manifest_fails_closed(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text('{"items": "not-a-list"}')

    result = service(path).inventory()

    assert result["configured"] is False
    assert result["status"] == "INVALID_CONFIG"
    assert result["items"] == []
