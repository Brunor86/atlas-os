from dataclasses import dataclass, field
from datetime import datetime

from atlas.models.alert import Alert


@dataclass(slots=True)
class HealthInfo:

    status: str

    alerts: list[Alert] = field(default_factory=list)

    warnings: list[Alert] = field(default_factory=list)

    last_update: str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
