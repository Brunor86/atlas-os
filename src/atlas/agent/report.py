from dataclasses import dataclass, field
from datetime import datetime
from atlas.core.asset import Asset

@dataclass(slots=True)
class AgentReport:

    agent_id: str

    hostname: str

    timestamp: datetime = field(
        default_factory=datetime.now
    )

    assets: list[Asset] = field(
        default_factory=list
    )

    def add_asset(self, asset):

        self.assets.append(asset)
