from dataclasses import dataclass, field
import uuid
from typing import List, Dict
from atlas.models.incident_intelligence import IncidentIntelligence


@dataclass
class NOCIssue:

    service: str
    issue_type: str
    severity: str
    description: str



@dataclass
class NOCIncident:

    name: str
    confidence: float
    reason: str

    id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    # Persistent operational identity (INC-xxxx).
    #
    # id is the internal NOC UUID.
    # incident_id is the persistent IncidentManager identifier.
    incident_id: str = ""

    asset: str = "unknown"

    affected_assets: list = field(
        default_factory=list
    )

    events: list = field(default_factory=list)

    impact: list = field(default_factory=list)


    root_cause: str = ""

    diagnosis: str = ""

    blast_radius: list = field(
        default_factory=list
    )


    supporting_infrastructure: list = field(
        default_factory=list
    )


    suggested_actions: list = field(
        default_factory=list
    )


    evidence: list = field(
        default_factory=list
    )



    severity: str = "UNKNOWN"

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


    recommendation: dict = field(
        default_factory=dict
    )


    safe_action: dict = field(
        default_factory=dict
    )


    approval_context: dict = field(
        default_factory=dict
    )


    action_proposal: dict = field(
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


    memory: dict = field(
        default_factory=dict
    )


    memory_intelligence: dict = field(
        default_factory=dict
    )


    decision: dict = field(
        default_factory=dict
    )


    lifecycle: list = field(
        default_factory=list
    )


    intelligence: IncidentIntelligence = field(
        default_factory=IncidentIntelligence
    )


    # AI operator reasoning
    ai_analysis: dict = field(
        default_factory=dict
    )

    ai_reasoning: list = field(
        default_factory=list
    )

    ai_recommendation: str = ""

    ai_confidence: float = 0.0

@dataclass
class NOCStatus:

    status: str
    score: int
    priority: str
    summary: str

    active_events: int = 0
    critical_services: int = 0

    services: Dict = field(default_factory=dict)

    issues: List[NOCIssue] = field(default_factory=list)

    incidents: List[NOCIncident] = field(default_factory=list)

    recommendations: List[str] = field(default_factory=list)
    explanations: List[str] = field(default_factory=list)

    operator_explanation: list = field(
        default_factory=list
    )


    def to_dict(self):

        return {

            "status": self.status,

            "noc_score": self.score,

            "priority": self.priority,

            "summary": self.summary,


            "active_events": self.active_events,

            "critical_services": self.critical_services,


            "services": self.services,


            "issues": [

                {
                    "service": i.service,

                    "type": i.issue_type,

                    "severity": i.severity,

                      "incident_score": i.incident_score,

                    "description": i.description,
                }

                for i in self.issues

            ],


            "incidents": [

                {
                    "name": i.name,

                    "confidence": i.confidence,

                    "severity": i.severity,

                    "incident_score": i.incident_score,

                    "reason": i.reason,

                    "root_cause": i.root_cause,

                    "diagnosis": i.diagnosis,

                    "blast_radius": i.blast_radius,

                    "supporting_infrastructure": i.supporting_infrastructure,

                    "suggested_actions": i.suggested_actions,

                    "evidence": i.evidence,

                    "events": i.events,

                    "impact": i.impact,

                    "intelligence": (
                        i.intelligence.to_dict()
                        if i.intelligence
                        else {}
                    ),

                    "impact_intelligence": (
                        i.impact_intelligence
                        if i.impact_intelligence
                        else {}
                    ),

                    "action_proposal": (
                        i.action_proposal
                        if i.action_proposal
                        else {}
                    ),

                }

                for i in self.incidents

            ],

            "explanations": self.explanations,
            "recommendations": self.recommendations,

            "operator_explanation": self.operator_explanation,

        }
