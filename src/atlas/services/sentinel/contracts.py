from dataclasses import (
    dataclass,
    field,
    replace,
)
from datetime import datetime
from enum import StrEnum
from typing import Any, Mapping


class SentinelSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class SentinelState(StrEnum):
    OPEN = "OPEN"
    RECOVERED = "RECOVERED"


SEVERITY_RANK = {
    SentinelSeverity.INFO: 10,
    SentinelSeverity.WARNING: 20,
    SentinelSeverity.CRITICAL: 30,
}


@dataclass(
    frozen=True,
    slots=True,
)
class SentinelFinding:
    fingerprint: str
    source: str
    kind: str
    subject: str
    severity: SentinelSeverity
    state: SentinelState
    title: str
    summary: str
    observed_at: datetime

    evidence: Mapping[str, Any] = field(
        default_factory=dict
    )

    def recovered(
        self,
        *,
        observed_at: datetime,
    ):
        return replace(
            self,
            state=SentinelState.RECOVERED,
            observed_at=observed_at,
            title=f"Recovered: {self.title}",
            summary=(
                "Condition returned to normal. "
                f"Previous finding: {self.summary}"
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SentinelNotification:
    finding: SentinelFinding
    reason: str
