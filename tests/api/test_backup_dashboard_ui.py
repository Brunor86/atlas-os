from pathlib import Path

from jinja2 import (
    Environment,
    FileSystemLoader,
)


ROOT = (
    Path(__file__).resolve()
    .parents[2]
)

INDEX = (
    ROOT
    / "src/atlas/api/templates/index.html"
)

PARTIAL = (
    ROOT
    / "src/atlas/api/templates/partials/backup_recovery.html"
)

CSS = (
    ROOT
    / "src/atlas/api/static/css/atlas.css"
)

SERVER = (
    ROOT
    / "src/atlas/api/server.py"
)


def normalized(path):

    return " ".join(
        path.read_text().split()
    )


def test_backup_dashboard_is_wired_to_home():

    index = normalized(INDEX)
    server = normalized(SERVER)

    assert (
        "partials/backup_recovery.html"
        in index
    )

    assert (
        "BackupInventoryService"
        in server
    )

    assert (
        '"backups": backup_inventory'
        in server
    )


def test_backup_dashboard_has_protection_states():

    html = normalized(PARTIAL)
    css = normalized(CSS)

    assert "backupRecovery" in html
    assert "backups.summary.protected" in html
    assert "backups.summary.missing" in html

    assert ".backup-state.healthy" in css
    assert ".backup-state.stale" in css
    assert ".backup-state.failed" in css
    assert ".backup-state.missing" in css
    assert ".backup-state.excluded" in css
    assert ".backup-state.unobserved" in css
    assert ".backup-job-value.healthy" in css
    assert ".backup-job-value.failed" in css
    assert "backups.job_summary.healthy" in html
    assert "item.job.status" in html


def test_backup_dashboard_renders_missing_gap():

    templates = (
        ROOT
        / "src/atlas/api/templates"
    )

    environment = Environment(
        loader=FileSystemLoader(
            templates
        )
    )

    template = environment.get_template(
        "partials/backup_recovery.html"
    )

    rendered = template.render(
        backups={
            "configured": True,
            "status": "STALE",
            "summary": {
                "total": 2,
                "protected": 1,
                "healthy": 1,
                "stale": 0,
                "failed": 0,
                "missing": 1,
                "excluded": 0,
            },
            "job_summary": {
                "configured": 1,
                "healthy": 1,
                "failed": 0,
                "unobserved": 0,
            },
            "items": [
                {
                    "name": "ATLAS SQLite",
                    "asset": "ATLAS OS",
                    "kind": "database",
                    "status": "HEALTHY",
                    "policy": "daily",
                    "age_hours": 4.0,
                    "integrity": "RECORDED",
                    "retention_days": 14,
                    "detail": "within policy",
                    "job": {
                        "status": "HEALTHY",
                        "provider": "local",
                        "timer": "atlas-backup.timer",
                        "service": "atlas-backup.service",
                        "detail": "timer is healthy",
                    },
                },
                {
                    "name": "Immich originals",
                    "asset": "Immich",
                    "kind": "independent-copy",
                    "status": "MISSING",
                    "policy": "independent copy",
                    "age_hours": None,
                    "integrity": "NOT_RECORDED",
                    "retention_days": None,
                    "detail": "artifact directory missing",
                    "job": {
                        "status": "NOT_APPLICABLE",
                        "provider": None,
                        "timer": None,
                        "service": None,
                        "detail": "no observable timer configured",
                    },
                },
            ],
        }
    )

    assert "13" not in rendered
    assert "Protection gap detected" in rendered
    assert "Immich originals" in rendered
    assert "MISSING" in rendered
    assert "ATLAS SQLite" in rendered
    assert "HEALTHY" in rendered
    assert "Jobs healthy" in rendered
    assert "NOT_APPLICABLE" in rendered




def test_backup_dashboard_polish_contract():

    html = normalized(PARTIAL)
    css = normalized(CSS)

    assert (
        "<h3> Backup & Recovery </h3>"
        not in html
    )

    assert "Protection gaps" in html

    assert (
        "backup-item backup-item-{{ item.status|lower }}"
        in html
    )

    assert (
        "item.job.status in [\"FAILED\", \"UNOBSERVED\"]"
        in html
    )

    assert ".backup-item-failed" in css
    assert ".backup-item-missing" in css
    assert ".backup-item-stale" in css
    assert ".backup-item-healthy" in css
    assert ".backup-item-excluded" in css
