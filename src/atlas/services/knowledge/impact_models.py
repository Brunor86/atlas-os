from dataclasses import dataclass, field



@dataclass(slots=True)
class ImpactResult:


    asset_id: str


    asset_name: str


    asset_type: str


    roles: list[str] = field(
        default_factory=list
    )


    depth: int = 0


    reason: str = ""


    relationship: str = ""


    criticality: str = "UNKNOWN"


    impact_score: int = 0



@dataclass(slots=True)
class ImpactReport:


    asset_id: str


    asset_name: str


    severity: str


    score: int


    blast_radius: int


    affected: list[ImpactResult] = field(
        default_factory=list
    )
