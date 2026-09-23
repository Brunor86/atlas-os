from dataclasses import dataclass, field


@dataclass
class LearningRecord:

    incident_id: str

    action: str

    result: str

    resolution: str = ""

    confidence: float = 0.0

    evidence: list = field(
        default_factory=list
    )
