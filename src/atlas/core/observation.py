from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class Observation:

    asset_id: str

    type: str

    value: object

    severity: str

    source: str

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
