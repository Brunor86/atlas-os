from datetime import (
    UTC,
    datetime,
)

from atlas.services.backup_intelligence.inventory import (
    BackupInventoryService,
)
from atlas.services.control_plane.health import (
    ControlPlaneHealthService,
)
from atlas.services.sentinel.contracts import (
    SentinelFinding,
    SentinelSeverity,
    SentinelState,
)
from atlas.services.sentinel.fingerprint import (
    sentinel_fingerprint,
)
from atlas.storage.incident_repository import (
    IncidentRepository,
)


def _now():
    return datetime.now(
        UTC
    )


def _incident_severity(
    raw,
):
    value = str(
        raw or ""
    ).strip().upper()

    if value in {
        "CRITICAL",
        "SEVERE",
    }:
        return (
            SentinelSeverity.CRITICAL
        )

    if value in {
        "HIGH",
        "MEDIUM",
        "WARNING",
        "WARN",
        "UNKNOWN",
        "",
    }:
        return (
            SentinelSeverity.WARNING
        )

    return SentinelSeverity.INFO


class IncidentSource:
    name = "incidents"

    def __init__(
        self,
        *,
        repository=None,
    ):
        self.repository = (
            repository
            or IncidentRepository()
        )

    def collect(
        self,
        *,
        observed_at=None,
    ):
        observed_at = (
            observed_at
            or _now()
        )

        findings = []

        for record in (
            self.repository
            .get_active_records()
        ):
            incident_id = str(
                record.get("id")
                or "unknown"
            )

            title = str(
                record.get("title")
                or "ATLAS incident"
            )

            asset = str(
                record.get("asset_id")
                or "unknown asset"
            )

            raw_severity = str(
                record.get("severity")
                or "UNKNOWN"
            ).upper()

            severity = (
                _incident_severity(
                    raw_severity
                )
            )

            findings.append(
                SentinelFinding(
                    fingerprint=(
                        sentinel_fingerprint(
                            source="incident",
                            kind="open_incident",
                            subject=incident_id,
                        )
                    ),
                    source="incident",
                    kind="open_incident",
                    subject=incident_id,
                    severity=severity,
                    state=(
                        SentinelState.OPEN
                    ),
                    title=title,
                    summary=(
                        f"{incident_id} is open "
                        f"for {asset}. "
                        f"ATLAS severity="
                        f"{raw_severity}."
                    ),
                    observed_at=(
                        observed_at
                    ),
                    evidence={
                        "incident_id":
                            incident_id,
                        "asset_id":
                            asset,
                        "severity":
                            raw_severity,
                        "status":
                            record.get(
                                "status"
                            ),
                    },
                )
            )

        return findings


class BackupSource:
    name = "backups"

    def __init__(
        self,
        *,
        service=None,
    ):
        self.service = (
            service
            or BackupInventoryService()
        )

    def collect(
        self,
        *,
        observed_at=None,
    ):
        observed_at = (
            observed_at
            or _now()
        )

        data = self.service.inventory()

        findings = []

        configured = bool(
            data.get("configured")
        )

        overall = str(
            data.get("status")
            or "UNKNOWN"
        ).upper()

        error = data.get(
            "error"
        )

        summary = dict(
            data.get("summary")
            or {}
        )

        jobs = dict(
            data.get("job_summary")
            or {}
        )

        if not configured:
            findings.append(
                SentinelFinding(
                    fingerprint=(
                        sentinel_fingerprint(
                            source="backup",
                            kind=(
                                "backup_not_configured"
                            ),
                            subject=(
                                "backup_inventory"
                            ),
                        )
                    ),
                    source="backup",
                    kind=(
                        "backup_not_configured"
                    ),
                    subject="backup_inventory",
                    severity=(
                        SentinelSeverity.WARNING
                    ),
                    state=(
                        SentinelState.OPEN
                    ),
                    title=(
                        "Backup protection "
                        "is not configured"
                    ),
                    summary=(
                        "ATLAS Backup Intelligence "
                        "has no active backup "
                        "configuration."
                    ),
                    observed_at=(
                        observed_at
                    ),
                    evidence={
                        "status":
                            overall,
                    },
                )
            )

        if error:
            findings.append(
                SentinelFinding(
                    fingerprint=(
                        sentinel_fingerprint(
                            source="backup",
                            kind=(
                                "backup_inventory_error"
                            ),
                            subject=(
                                "backup_inventory"
                            ),
                        )
                    ),
                    source="backup",
                    kind=(
                        "backup_inventory_error"
                    ),
                    subject="backup_inventory",
                    severity=(
                        SentinelSeverity.CRITICAL
                    ),
                    state=(
                        SentinelState.OPEN
                    ),
                    title=(
                        "Backup Intelligence "
                        "error"
                    ),
                    summary=str(
                        error
                    ),
                    observed_at=(
                        observed_at
                    ),
                    evidence={
                        "status":
                            overall,
                    },
                )
            )

        failed = int(
            summary.get(
                "failed",
                0,
            )
            or 0
        )

        missing = int(
            summary.get(
                "missing",
                0,
            )
            or 0
        )

        stale = int(
            summary.get(
                "stale",
                0,
            )
            or 0
        )

        if (
            failed
            or missing
            or stale
        ):
            severity = (
                SentinelSeverity.CRITICAL
                if failed
                else SentinelSeverity.WARNING
            )

            parts = []

            if failed:
                parts.append(
                    f"{failed} failed"
                )

            if missing:
                parts.append(
                    f"{missing} missing"
                )

            if stale:
                parts.append(
                    f"{stale} stale"
                )

            healthy = int(
                summary.get(
                    "healthy",
                    0,
                )
                or 0
            )

            total = int(
                summary.get(
                    "total",
                    0,
                )
                or 0
            )

            findings.append(
                SentinelFinding(
                    fingerprint=(
                        sentinel_fingerprint(
                            source="backup",
                            kind=(
                                "backup_protection_gap"
                            ),
                            subject=(
                                "backup_inventory"
                            ),
                        )
                    ),
                    source="backup",
                    kind=(
                        "backup_protection_gap"
                    ),
                    subject="backup_inventory",
                    severity=severity,
                    state=(
                        SentinelState.OPEN
                    ),
                    title=(
                        "Backup protection "
                        "requires attention"
                    ),
                    summary=(
                        ", ".join(parts)
                        + " backup target(s). "
                        + f"{healthy}/{total} "
                        + "currently healthy."
                    ),
                    observed_at=(
                        observed_at
                    ),
                    evidence={
                        "status":
                            overall,
                        "summary":
                            summary,
                    },
                )
            )

        job_failed = int(
            jobs.get(
                "failed",
                0,
            )
            or 0
        )

        job_unobserved = int(
            jobs.get(
                "unobserved",
                0,
            )
            or 0
        )

        if job_failed:
            findings.append(
                SentinelFinding(
                    fingerprint=(
                        sentinel_fingerprint(
                            source="backup",
                            kind=(
                                "backup_job_failure"
                            ),
                            subject=(
                                "backup_jobs"
                            ),
                        )
                    ),
                    source="backup",
                    kind=(
                        "backup_job_failure"
                    ),
                    subject="backup_jobs",
                    severity=(
                        SentinelSeverity.CRITICAL
                    ),
                    state=(
                        SentinelState.OPEN
                    ),
                    title=(
                        "Backup job failure"
                    ),
                    summary=(
                        f"{job_failed} configured "
                        "backup job(s) are failing."
                    ),
                    observed_at=(
                        observed_at
                    ),
                    evidence={
                        "job_summary":
                            jobs,
                    },
                )
            )

        if job_unobserved:
            findings.append(
                SentinelFinding(
                    fingerprint=(
                        sentinel_fingerprint(
                            source="backup",
                            kind=(
                                "backup_job_unobserved"
                            ),
                            subject=(
                                "backup_jobs"
                            ),
                        )
                    ),
                    source="backup",
                    kind=(
                        "backup_job_unobserved"
                    ),
                    subject="backup_jobs",
                    severity=(
                        SentinelSeverity.WARNING
                    ),
                    state=(
                        SentinelState.OPEN
                    ),
                    title=(
                        "Backup job health "
                        "cannot be observed"
                    ),
                    summary=(
                        f"{job_unobserved} "
                        "configured backup "
                        "job(s) are unobserved."
                    ),
                    observed_at=(
                        observed_at
                    ),
                    evidence={
                        "job_summary":
                            jobs,
                    },
                )
            )

        if (
            overall
            in {
                "STALE",
                "FAILED",
                "MISSING",
            }
            and not (
                failed
                or missing
                or stale
                or error
            )
        ):
            severity = (
                SentinelSeverity.CRITICAL
                if overall == "FAILED"
                else SentinelSeverity.WARNING
            )

            findings.append(
                SentinelFinding(
                    fingerprint=(
                        sentinel_fingerprint(
                            source="backup",
                            kind=(
                                "backup_overall_status"
                            ),
                            subject=(
                                "backup_inventory"
                            ),
                        )
                    ),
                    source="backup",
                    kind=(
                        "backup_overall_status"
                    ),
                    subject="backup_inventory",
                    severity=severity,
                    state=(
                        SentinelState.OPEN
                    ),
                    title=(
                        "Backup Intelligence "
                        f"is {overall.lower()}"
                    ),
                    summary=(
                        "Backup Intelligence "
                        f"overall status={overall}."
                    ),
                    observed_at=(
                        observed_at
                    ),
                    evidence={
                        "status":
                            overall,
                        "summary":
                            summary,
                    },
                )
            )

        return findings


class AtlasHealthSource:
    name = "atlas_health"

    def __init__(
        self,
        *,
        service=None,
    ):
        self.service = (
            service
            or ControlPlaneHealthService()
        )

    @staticmethod
    def _severity(
        status,
    ):
        value = str(
            status or ""
        ).upper()

        if value == "UNHEALTHY":
            return (
                SentinelSeverity.CRITICAL
            )

        return (
            SentinelSeverity.WARNING
        )

    def collect(
        self,
        *,
        observed_at=None,
    ):
        observed_at = (
            observed_at
            or _now()
        )

        data = self.service.status()

        components = dict(
            data.get("components")
            or {}
        )

        findings = []

        for (
            component_name,
            component,
        ) in components.items():
            component = dict(
                component
                or {}
            )

            status = str(
                component.get("status")
                or "UNKNOWN"
            ).upper()

            if status == "HEALTHY":
                continue

            reason = str(
                component.get("reason")
                or "UNKNOWN"
            )

            findings.append(
                SentinelFinding(
                    fingerprint=(
                        sentinel_fingerprint(
                            source=(
                                "atlas_control_plane"
                            ),
                            kind=(
                                "component_health"
                            ),
                            subject=(
                                component_name
                            ),
                        )
                    ),
                    source=(
                        "atlas_control_plane"
                    ),
                    kind=(
                        "component_health"
                    ),
                    subject=(
                        component_name
                    ),
                    severity=(
                        self._severity(
                            status
                        )
                    ),
                    state=(
                        SentinelState.OPEN
                    ),
                    title=(
                        "ATLAS component "
                        f"{component_name} "
                        f"is {status.lower()}"
                    ),
                    summary=(
                        f"{component_name}: "
                        f"status={status}, "
                        f"reason={reason}."
                    ),
                    observed_at=(
                        observed_at
                    ),
                    evidence={
                        "component":
                            component_name,
                        "status":
                            status,
                        "reason":
                            reason,
                    },
                )
            )

        overall = str(
            data.get("status")
            or "UNKNOWN"
        ).upper()

        if (
            overall != "HEALTHY"
            and not findings
        ):
            findings.append(
                SentinelFinding(
                    fingerprint=(
                        sentinel_fingerprint(
                            source=(
                                "atlas_control_plane"
                            ),
                            kind=(
                                "overall_health"
                            ),
                            subject=(
                                "ATLAS_CONTROL_PLANE"
                            ),
                        )
                    ),
                    source=(
                        "atlas_control_plane"
                    ),
                    kind=(
                        "overall_health"
                    ),
                    subject=(
                        "ATLAS_CONTROL_PLANE"
                    ),
                    severity=(
                        self._severity(
                            overall
                        )
                    ),
                    state=(
                        SentinelState.OPEN
                    ),
                    title=(
                        "ATLAS control plane "
                        f"is {overall.lower()}"
                    ),
                    summary=(
                        "ATLAS control plane "
                        f"status={overall}."
                    ),
                    observed_at=(
                        observed_at
                    ),
                    evidence={
                        "status":
                            overall,
                    },
                )
            )

        return findings
