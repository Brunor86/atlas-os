from dataclasses import dataclass


@dataclass
class IncidentLifecycleEvent:

    state: str

    timestamp: str

    detail: str = ""

    actor: str = "ATLAS"
