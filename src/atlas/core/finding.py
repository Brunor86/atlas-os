from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class HealthFinding:

    asset_id: str

    severity: str

    title: str

    message: str

    category: str

    created_at: datetime = None

    last_seen: datetime = None

    occurrences: int = 1


    def key(self):

        return (
            f"{self.asset_id}:"
            f"{self.category}:"
            f"{self.title}"
        )

