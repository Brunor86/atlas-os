from dataclasses import dataclass, field


@dataclass
class ActionExecution:

    approval_id: str

    incident_id: str = ""

    action: str = ""

    target: str = ""

    status: str = "PENDING"

    result: str = ""

    executed_at: str = ""

    evidence: list = field(
        default_factory=list
    )

    verification: dict = field(
        default_factory=dict
    )
