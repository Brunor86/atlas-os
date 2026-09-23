from dataclasses import dataclass, field


@dataclass
class ImpactNode:

    asset_id: str

    relationship: str

    depth: int = 0

    weight: int = 0

    impact_score: float = 0.0



@dataclass
class ImpactGraph:

    root_asset: str

    severity: str

    score: int

    upstream: list[ImpactNode] = field(
        default_factory=list
    )

    downstream: list[ImpactNode] = field(
        default_factory=list
    )

    root_causes: list[ImpactNode] = field(
        default_factory=list
    )
