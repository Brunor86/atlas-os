from dataclasses import asdict, dataclass
from enum import StrEnum


class BackupStatus(StrEnum):
    HEALTHY = "HEALTHY"
    STALE = "STALE"
    FAILED = "FAILED"
    MISSING = "MISSING"
    EXCLUDED = "EXCLUDED"


class BackupIntegrity(StrEnum):
    RECORDED = "RECORDED"
    NOT_RECORDED = "NOT_RECORDED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(slots=True)
class BackupItem:
    id: str
    name: str
    asset: str
    kind: str
    status: BackupStatus
    policy: str
    artifact: str | None
    last_backup: str | None
    age_hours: float | None
    max_age_hours: float | None
    retention_days: int | None
    integrity: BackupIntegrity
    timer: str | None
    detail: str | None

    def as_dict(self) -> dict:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["integrity"] = self.integrity.value
        return payload
