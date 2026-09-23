from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class AgentInfo:

    id: str

    hostname: str

    capabilities: list[str] = field(
        default_factory=list
    )

    last_seen: datetime = field(
        default_factory=datetime.now
    )
