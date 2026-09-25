import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from atlas.models.backup import (
    BackupIntegrity,
    BackupItem,
    BackupStatus,
)

from atlas.services.backup_intelligence.job_health import (
    BackupJobStatus,
    SystemdJobHealthService,
)


class BackupInventoryService:
    """Read-only backup inventory and freshness evaluator."""

    def __init__(
        self,
        manifest_path: str | Path | None = None,
        now: Callable[[], datetime] | None = None,
        job_runner: Callable | None = None,
    ):
        configured = (
            manifest_path
            or os.getenv(
                "ATLAS_BACKUP_MANIFEST",
                "/etc/atlas/backup-intelligence.json",
            )
        )

        self.manifest_path = Path(configured)
        self._now = now or (
            lambda: datetime.now(timezone.utc)
        )

        self._job_runner = job_runner

    def inventory(self) -> dict:
        if not self.manifest_path.is_file():
            return self._empty(
                status="NOT_CONFIGURED",
                error=None,
            )

        try:
            manifest = json.loads(
                self.manifest_path.read_text()
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            return self._empty(
                status="INVALID_CONFIG",
                error=str(exc),
            )

        definitions = manifest.get(
            "items"
        )

        if not isinstance(
            definitions,
            list,
        ):
            return self._empty(
                status="INVALID_CONFIG",
                error="manifest items must be a list",
            )

        providers = manifest.get(
            "providers",
            {},
        )

        if not isinstance(
            providers,
            dict,
        ):
            return self._empty(
                status="INVALID_CONFIG",
                error="manifest providers must be an object",
            )

        observer = SystemdJobHealthService(
            providers=providers,
            runner=self._job_runner,
        )

        valid_definitions = [
            definition
            for definition in definitions
            if isinstance(
                definition,
                dict,
            )
        ]

        evaluated = []
        job_cache = {}

        for definition in valid_definitions:

            item = self._evaluate(
                definition
            )

            provider_name = self._optional_text(
                definition.get(
                    "job_provider"
                )
            )

            if item.timer:

                key = (
                    provider_name or "",
                    item.timer,
                )

                job = job_cache.get(
                    key
                )

                if job is None:

                    job = observer.evaluate(
                        provider_name,
                        item.timer,
                    )

                    job_cache[key] = job

            else:

                job = observer.evaluate(
                    provider_name,
                    None,
                )

            evaluated.append(
                (
                    item,
                    job,
                )
            )

        items = [
            item
            for item, _job in evaluated
        ]

        summary = {
            "total": len(items),
            "protected": sum(
                item.status
                in {
                    BackupStatus.HEALTHY,
                    BackupStatus.STALE,
                }
                for item in items
            ),
            "healthy": sum(
                item.status
                == BackupStatus.HEALTHY
                for item in items
            ),
            "stale": sum(
                item.status
                == BackupStatus.STALE
                for item in items
            ),
            "failed": sum(
                item.status
                == BackupStatus.FAILED
                for item in items
            ),
            "missing": sum(
                item.status
                == BackupStatus.MISSING
                for item in items
            ),
            "excluded": sum(
                item.status
                == BackupStatus.EXCLUDED
                for item in items
            ),
        }

        job_summary = {
            "configured": len(
                job_cache
            ),
            "healthy": sum(
                job.status
                == BackupJobStatus.HEALTHY
                for job in job_cache.values()
            ),
            "failed": sum(
                job.status
                == BackupJobStatus.FAILED
                for job in job_cache.values()
            ),
            "unobserved": sum(
                job.status
                == BackupJobStatus.UNOBSERVED
                for job in job_cache.values()
            ),
        }

        overall = self._overall(
            summary,
            job_summary,
        )

        return {
            "configured": True,
            "status": overall,
            "manifest_version": manifest.get(
                "version",
                1,
            ),
            "generated_at":
                self._normalized_now().isoformat(),
            "summary": summary,
            "job_summary": job_summary,
            "items": [
                {
                    **item.as_dict(),
                    "job":
                        job.as_dict(),
                }
                for item, job in evaluated
            ],
            "integrity_mode":
                "RECORDED_CHECKSUM_ONLY",
            "error": None,
        }

    def _evaluate(
        self,
        definition: dict,
    ) -> BackupItem:
        item_id = str(
            definition.get(
                "id",
                "",
            )
            or ""
        ).strip()

        name = str(
            definition.get(
                "name",
                item_id,
            )
            or item_id
        ).strip()

        asset = str(
            definition.get(
                "asset",
                name,
            )
            or name
        ).strip()

        kind = str(
            definition.get(
                "kind",
                "artifact",
            )
            or "artifact"
        ).strip()

        policy = str(
            definition.get(
                "policy",
                "unspecified",
            )
            or "unspecified"
        ).strip()

        timer = self._optional_text(
            definition.get(
                "timer"
            )
        )

        retention_days = self._optional_int(
            definition.get(
                "retention_days"
            )
        )

        max_age_hours = self._optional_float(
            definition.get(
                "max_age_hours"
            )
        )

        if bool(
            definition.get(
                "excluded",
                False,
            )
        ):
            return BackupItem(
                id=item_id,
                name=name,
                asset=asset,
                kind=kind,
                status=BackupStatus.EXCLUDED,
                policy=policy,
                artifact=None,
                last_backup=None,
                age_hours=None,
                max_age_hours=max_age_hours,
                retention_days=retention_days,
                integrity=(
                    BackupIntegrity.NOT_APPLICABLE
                ),
                timer=timer,
                detail=self._optional_text(
                    definition.get(
                        "reason"
                    )
                ),
            )

        directory_value = self._optional_text(
            definition.get(
                "artifact_dir"
            )
        )

        pattern = self._optional_text(
            definition.get(
                "artifact_pattern"
            )
        )

        if not directory_value or not pattern:
            return BackupItem(
                id=item_id,
                name=name,
                asset=asset,
                kind=kind,
                status=BackupStatus.FAILED,
                policy=policy,
                artifact=None,
                last_backup=None,
                age_hours=None,
                max_age_hours=max_age_hours,
                retention_days=retention_days,
                integrity=(
                    BackupIntegrity.NOT_RECORDED
                ),
                timer=timer,
                detail="artifact policy incomplete",
            )

        directory = Path(
            directory_value
        )

        if not directory.is_dir():
            return BackupItem(
                id=item_id,
                name=name,
                asset=asset,
                kind=kind,
                status=BackupStatus.MISSING,
                policy=policy,
                artifact=None,
                last_backup=None,
                age_hours=None,
                max_age_hours=max_age_hours,
                retention_days=retention_days,
                integrity=(
                    BackupIntegrity.NOT_RECORDED
                ),
                timer=timer,
                detail="artifact directory missing",
            )

        candidates = [
            path
            for path in directory.glob(
                pattern
            )
            if path.is_file()
        ]

        if not candidates:
            return BackupItem(
                id=item_id,
                name=name,
                asset=asset,
                kind=kind,
                status=BackupStatus.MISSING,
                policy=policy,
                artifact=None,
                last_backup=None,
                age_hours=None,
                max_age_hours=max_age_hours,
                retention_days=retention_days,
                integrity=(
                    BackupIntegrity.NOT_RECORDED
                ),
                timer=timer,
                detail="no backup artifact found",
            )

        latest = max(
            candidates,
            key=lambda path:
                path.stat().st_mtime,
        )

        modified = datetime.fromtimestamp(
            latest.stat().st_mtime,
            tz=timezone.utc,
        )

        age_hours = max(
            0.0,
            (
                self._normalized_now()
                - modified
            ).total_seconds()
            / 3600,
        )

        status = BackupStatus.HEALTHY
        detail = "latest artifact is within policy"

        if (
            max_age_hours is not None
            and age_hours > max_age_hours
        ):
            status = BackupStatus.STALE
            detail = (
                "latest artifact exceeds "
                "maximum age"
            )

        checksum_suffix = str(
            definition.get(
                "checksum_suffix",
                ".sha256",
            )
        )

        integrity = (
            BackupIntegrity.RECORDED
            if Path(
                str(latest)
                + checksum_suffix
            ).is_file()
            else BackupIntegrity.NOT_RECORDED
        )

        return BackupItem(
            id=item_id,
            name=name,
            asset=asset,
            kind=kind,
            status=status,
            policy=policy,
            artifact=str(latest),
            last_backup=modified.isoformat(),
            age_hours=round(
                age_hours,
                3,
            ),
            max_age_hours=max_age_hours,
            retention_days=retention_days,
            integrity=integrity,
            timer=timer,
            detail=detail,
        )

    def _normalized_now(self) -> datetime:
        value = self._now()

        if value.tzinfo is None:
            return value.replace(
                tzinfo=timezone.utc
            )

        return value.astimezone(
            timezone.utc
        )

    @staticmethod
    def _overall(
        summary: dict,
        job_summary: dict,
    ) -> str:
        if (
            summary["failed"]
            or job_summary["failed"]
        ):
            return "FAILED"

        if (
            summary["missing"]
            or summary["stale"]
        ):
            return "STALE"

        if job_summary["unobserved"]:
            return "UNOBSERVED"

        if summary["protected"]:
            return "HEALTHY"

        return "NOT_CONFIGURED"

    @staticmethod
    def _optional_text(
        value,
    ) -> str | None:
        if value is None:
            return None

        text = str(
            value
        ).strip()

        return text or None

    @staticmethod
    def _optional_float(
        value,
    ) -> float | None:
        if value is None:
            return None

        try:
            result = float(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

        if result < 0:
            return None

        return result

    @staticmethod
    def _optional_int(
        value,
    ) -> int | None:
        if value is None:
            return None

        try:
            result = int(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

        if result < 0:
            return None

        return result

    def _empty(
        self,
        status: str,
        error: str | None,
    ) -> dict:
        return {
            "configured": False,
            "status": status,
            "manifest_version": None,
            "generated_at":
                self._normalized_now().isoformat(),
            "summary": {
                "total": 0,
                "protected": 0,
                "healthy": 0,
                "stale": 0,
                "failed": 0,
                "missing": 0,
                "excluded": 0,
            },
            "job_summary": {
                "configured": 0,
                "healthy": 0,
                "failed": 0,
                "unobserved": 0,
            },
            "items": [],
            "integrity_mode":
                "RECORDED_CHECKSUM_ONLY",
            "error": error,
        }
