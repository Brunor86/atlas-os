from dataclasses import dataclass


@dataclass(slots=True)
class CorrelatedIssue:

    asset_id: str

    category: str

    severity: str

    confidence: float

    signals: list[str]

    explanation: str
