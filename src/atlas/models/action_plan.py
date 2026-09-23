from dataclasses import dataclass, field


@dataclass
class ActionPlan:

    action: str

    target: str

    incident_id: str = ""

    reason: list = field(
        default_factory=list
    )

    evidence: list = field(
        default_factory=list
    )

    risk: str = "UNKNOWN"

    prerequisites: list = field(
        default_factory=list
    )

    rollback: str = ""

    confidence: float = 0.0

    def __getitem__(self, key):

        data = self.to_dict()

        #
        # Backward compatibility with the previous
        # dictionary-based recommendation contract.
        #
        if key == "status":
            return "reasoning_recommended"

        #
        # Dictionary consumers historically received
        # reasoning evidence wrapped with its pipeline source.
        # Keep attribute access on ActionPlan unchanged while
        # preserving that legacy dictionary representation.
        #
        if key == "evidence":

            return [
                {
                    "source": "reasoning",
                    "observation": dict(item),
                }
                if (
                    isinstance(item, dict)
                    and "observation" not in item
                )
                else item
                for item in data["evidence"]
            ]

        return data[key]


    def get(self, key, default=None):

        #
        # Backward compatibility with the previous
        # dictionary-based recommendation contract.
        #
        try:
            return self[key]
        except KeyError:
            return default


    def to_dict(self):

        return {
            "action": self.action,
            "target": self.target,
            "incident_id": self.incident_id,
            "reason": self.reason,
            "evidence": self.evidence,
            "risk": self.risk,
            "prerequisites": self.prerequisites,
            "rollback": self.rollback,
            "confidence": self.confidence,
        }
