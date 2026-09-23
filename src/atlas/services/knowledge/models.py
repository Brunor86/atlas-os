from dataclasses import dataclass, field



@dataclass(slots=True)
class KnowledgeCard:


    asset_id: str

    asset_name: str

    asset_type: str


    summary: str = ""


    roles: list[str] = field(
        default_factory=list
    )


    #
    # Infrastructure relationships
    #

    dependencies: list[str] = field(
        default_factory=list
    )


    dependents: list[str] = field(
        default_factory=list
    )


    #
    # Application knowledge relationships
    #

    application_dependencies: list[str] = field(
        default_factory=list
    )


    observations: list[str] = field(
        default_factory=list
    )


    #
    # Root cause / impact intelligence
    #

    impact_reasons: list[str] = field(
        default_factory=list
    )


    #
    # Intelligence metadata
    #

    criticality: str = "UNKNOWN"


    role_weight: int = 0


    relationship_count: int = 0


    impact_score: int = 0


    blast_radius: int = 0


    health_score: float = 100.0

    risk_score: int = 0

    operational_summary: str = ""


    recommendations: list[str] = field(
        default_factory=list
    )


    capabilities: list[str] = field(
        default_factory=list
    )
