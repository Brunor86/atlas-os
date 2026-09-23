from dataclasses import dataclass, field


@dataclass
class AssetContext:
    """
    Enriched operational context for an infrastructure asset.

    This model represents an asset after topology,
    roles and relationships have been resolved.
    """

    id: str
    name: str
    type: str

    status: str = "UNKNOWN"

    criticality: str = "MEDIUM"

    roles: list[str] = field(default_factory=list)

    weight: int = 0

    capabilities: list[str] = field(default_factory=list)

    parents: list[str] = field(default_factory=list)

    children: list[str] = field(default_factory=list)

    impact_path: list[str] = field(default_factory=list)
