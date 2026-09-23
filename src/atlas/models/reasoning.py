from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict


@dataclass
class ReasoningStep:


    stage: str

    title: str

    data: Dict[str, Any] = field(
        default_factory=dict
    )

    confidence: float = 0.0

    timestamp: str = field(
        default_factory=lambda:
            datetime.now(UTC).isoformat()
    )


    def to_dict(
        self,
    ):

        return {

            "stage": self.stage,

            "title": self.title,

            "data": self.data,

            "confidence": self.confidence,

            "timestamp": self.timestamp,

        }
