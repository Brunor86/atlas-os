from datetime import (
    datetime,
    timezone,
)

from atlas.services.sentinel import (
    AtlasHealthSource,
    BackupSource,
    IncidentSource,
    SentinelSeverity,
)


NOW = datetime(
    2026,
    10,
    7,
    2,
    30,
    tzinfo=timezone.utc,
)


class FakeIncidentRepository:
    def __init__(
        self,
        records,
    ):
        self.records = records

    def get_active_records(self):
        return self.records


class FakeBackupService:
    def __init__(
        self,
        payload,
    ):
        self.payload = payload

    def inventory(self):
        return self.payload


class FakeHealthService:
    def __init__(
        self,
        payload,
    ):
        self.payload = payload

    def status(self):
        return self.payload


def test_active_medium_incident_is_warning():
    source = IncidentSource(
        repository=(
            FakeIncidentRepository(
                [
                    {
                        "id": "INC-9",
                        "title":
                            "Service degradation",
                        "asset_id":
                            "container-x",
                        "severity":
                            "MEDIUM",
                        "status":
                            "OPEN",
                    }
                ]
            )
        )
    )

    findings = source.collect(
        observed_at=NOW
    )

    assert len(findings) == 1

    assert (
        findings[0].severity
        == SentinelSeverity.WARNING
    )

    assert (
        findings[0].subject
        == "INC-9"
    )


def test_active_critical_incident_is_critical():
    source = IncidentSource(
        repository=(
            FakeIncidentRepository(
                [
                    {
                        "id": "INC-10",
                        "title":
                            "Storage failure",
                        "asset_id":
                            "disk-x",
                        "severity":
                            "CRITICAL",
                        "status":
                            "OPEN",
                    }
                ]
            )
        )
    )

    findings = source.collect(
        observed_at=NOW
    )

    assert (
        findings[0].severity
        == SentinelSeverity.CRITICAL
    )


def test_backup_missing_target_is_warning():
    source = BackupSource(
        service=FakeBackupService(
            {
                "configured": True,
                "status": "STALE",
                "error": None,
                "summary": {
                    "total": 16,
                    "healthy": 13,
                    "stale": 0,
                    "failed": 0,
                    "missing": 1,
                    "excluded": 2,
                },
                "job_summary": {
                    "configured": 6,
                    "healthy": 6,
                    "failed": 0,
                    "unobserved": 0,
                },
            }
        )
    )

    findings = source.collect(
        observed_at=NOW
    )

    assert len(findings) == 1

    assert (
        findings[0].kind
        == "backup_protection_gap"
    )

    assert (
        findings[0].severity
        == SentinelSeverity.WARNING
    )


def test_backup_job_failure_is_critical():
    source = BackupSource(
        service=FakeBackupService(
            {
                "configured": True,
                "status": "FAILED",
                "error": None,
                "summary": {
                    "total": 5,
                    "healthy": 5,
                    "stale": 0,
                    "failed": 0,
                    "missing": 0,
                    "excluded": 0,
                },
                "job_summary": {
                    "configured": 2,
                    "healthy": 1,
                    "failed": 1,
                    "unobserved": 0,
                },
            }
        )
    )

    findings = source.collect(
        observed_at=NOW
    )

    critical = [
        finding
        for finding in findings
        if (
            finding.kind
            == "backup_job_failure"
        )
    ]

    assert len(critical) == 1

    assert (
        critical[0].severity
        == SentinelSeverity.CRITICAL
    )


def test_healthy_backups_generate_no_findings():
    source = BackupSource(
        service=FakeBackupService(
            {
                "configured": True,
                "status": "HEALTHY",
                "error": None,
                "summary": {
                    "total": 5,
                    "healthy": 5,
                    "stale": 0,
                    "failed": 0,
                    "missing": 0,
                    "excluded": 0,
                },
                "job_summary": {
                    "configured": 2,
                    "healthy": 2,
                    "failed": 0,
                    "unobserved": 0,
                },
            }
        )
    )

    assert not source.collect(
        observed_at=NOW
    )


def test_degraded_atlas_component_is_warning():
    source = AtlasHealthSource(
        service=FakeHealthService(
            {
                "status": "DEGRADED",
                "components": {
                    "collector": {
                        "status":
                            "DEGRADED",
                        "reason":
                            "CYCLE_STALE",
                    },
                    "database": {
                        "status":
                            "HEALTHY",
                        "reason":
                            "DATABASE_OK",
                    },
                },
            }
        )
    )

    findings = source.collect(
        observed_at=NOW
    )

    assert len(findings) == 1

    assert (
        findings[0].subject
        == "collector"
    )

    assert (
        findings[0].severity
        == SentinelSeverity.WARNING
    )


def test_unhealthy_atlas_component_is_critical():
    source = AtlasHealthSource(
        service=FakeHealthService(
            {
                "status": "UNHEALTHY",
                "components": {
                    "database": {
                        "status":
                            "UNHEALTHY",
                        "reason":
                            "DATABASE_UNAVAILABLE",
                    }
                },
            }
        )
    )

    findings = source.collect(
        observed_at=NOW
    )

    assert len(findings) == 1

    assert (
        findings[0].severity
        == SentinelSeverity.CRITICAL
    )
