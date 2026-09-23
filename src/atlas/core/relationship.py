
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum, auto


class RelationshipType(Enum):
    HOSTS = auto()
    RUNS_ON = auto()
    DEPENDS_ON = auto()
    USES = auto()
    CONNECTED_TO = auto()
    BACKS_UP = auto()
    MONITORS = auto()
    PROVIDES = auto()
    RUNS = auto()
    MANAGES = auto()


@dataclass(slots=True)
class Relationship:
    """
    Relación entre dos Assets.

    Una relación puede incorporar inteligencia propia:
    - confidence: confianza en la relación descubierta.
    - evidence: evidencia que justifica la relación.
    - metadata: información adicional no estructural.
    """

    source: str
    target: str
    type: RelationshipType

    confidence: float = 1.0

    evidence: list[str] = field(
        default_factory=list
    )

    metadata: dict = field(
        default_factory=dict
    )

    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )


_RELATIONSHIP_WEIGHTS = {
    RelationshipType.HOSTS: 100,
    RelationshipType.PROVIDES: 90,
    RelationshipType.DEPENDS_ON: 80,
    RelationshipType.MANAGES: 50,
    RelationshipType.RUNS: 40,
    RelationshipType.CONNECTED_TO: 30,
    RelationshipType.BACKS_UP: 20,
    RelationshipType.USES: 10,
    RelationshipType.MONITORS: 10,
    RelationshipType.RUNS_ON: 10,
}


_OPERATIONAL_RELATIONSHIPS = {
    RelationshipType.HOSTS,
    RelationshipType.DEPENDS_ON,
    RelationshipType.PROVIDES,
    RelationshipType.RUNS,
    RelationshipType.CONNECTED_TO,
    RelationshipType.RUNS_ON,
}


def relationship_weight(
    relationship_type: RelationshipType,
) -> int:
    return _RELATIONSHIP_WEIGHTS.get(
        relationship_type,
        1,
    )


def is_operational_relationship(
    relationship_type: RelationshipType,
) -> bool:
    return relationship_type in _OPERATIONAL_RELATIONSHIPS


def relationship_impact_score(
    relationship_type: RelationshipType,
    criticality_weight: int = 1,
) -> int:
    return (
        relationship_weight(
            relationship_type
        )
        * criticality_weight
    )
