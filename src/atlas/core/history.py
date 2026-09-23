from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(slots=True)
class AssetHistory:

    asset_id: str

    health: float

    status: str

    snapshot_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
