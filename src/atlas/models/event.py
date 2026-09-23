from dataclasses import dataclass, field


@dataclass
class Event:

    type: str

    title: str

    message: str

    first_seen: str

    last_seen: str

    status: str

    severity: str = "warning"

    asset_id: str | None = None

    data: dict = field(default_factory=dict)
