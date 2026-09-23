from dataclasses import dataclass, field


@dataclass
class SafeAction:

    action: str

    target: str

    incident_id: str = ""

    risk: str = "UNKNOWN"

    requires_approval: bool = True

    rollback: str = ""

    status: str = "PENDING_APPROVAL"

    evidence: list = field(
        default_factory=list
    )
