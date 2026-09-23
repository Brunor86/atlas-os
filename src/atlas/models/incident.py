from datetime import datetime, UTC
from dataclasses import dataclass, field
from atlas.models.incident_intelligence import IncidentIntelligence
from atlas.models.incident_execution import IncidentExecution
from atlas.models.incident_memory import IncidentMemory
from atlas.models.incident_timeline import IncidentTimeline


@dataclass
class Incident:

    id: str

    title: str

    asset: str

    severity: str

    status: str = "OPEN"


    evidence: list = field(
        default_factory=list
    )


    recommendations: list = field(
        default_factory=list
    )


    impact: list = field(
        default_factory=list
    )


    root_cause: str = ""


    diagnosis: str = ""


    blast_radius: list = field(
        default_factory=list
    )


    suggested_actions: list = field(
        default_factory=list
    )


    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )


    updated_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    intelligence: IncidentIntelligence = field(
        default_factory=IncidentIntelligence
    )

    execution: IncidentExecution = field(
        default_factory=IncidentExecution
    )

    memory_context: IncidentMemory = field(
        default_factory=IncidentMemory
    )

    timeline: IncidentTimeline = field(
        default_factory=IncidentTimeline
    )

    confidence: float = 0.0

    reason: str = ""

    incident_score: int = 0

    severity_context: dict = field(
        default_factory=dict
    )


    impact_intelligence: dict = field(
        default_factory=dict
    )


    reasoning_timeline: list = field(
        default_factory=list
    )


    memory_intelligence: dict = field(
        default_factory=dict
    )


    approval_context: dict = field(
        default_factory=dict
    )


    approval_policy: dict = field(
        default_factory=dict
    )


    execution_context: dict = field(
        default_factory=dict
    )


    remediation_context: dict = field(
        default_factory=dict
    )


    learning_context: dict = field(
        default_factory=dict
    )


    decision: dict = field(
        default_factory=dict
    )


    def update_status(
        self,
        status: str
    ):

        self.status = status

        self.updated_at = datetime.now(UTC)
