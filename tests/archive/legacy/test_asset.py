from atlas.core.asset import (
    Asset,
    AssetType,
    AssetStatus,
    Capability,
)
from atlas.core.observation import Observation
from atlas.core.observation import ObservationSeverity
from atlas.core.relationship import Relationship, RelationshipType


disk = Asset(
    id="storage-wd-red-pro",
    name="WD Red Pro 12TB",
    type=AssetType.STORAGE,
    status=AssetStatus.ONLINE,
)

disk.add_capability(Capability.SMART)
disk.add_capability(Capability.TEMPERATURE)

print(disk)

print("Online:", disk.is_online())
print("Healthy:", disk.is_healthy())
print("SMART:", disk.can(Capability.SMART))
print("Restart:", disk.can(Capability.RESTART))

disk.add_observation(
    Observation(
        category="temperature",
        value=40,
        severity=ObservationSeverity.WARNING,
        source="smartctl",
    )
)

disk.add_observation(
    Observation(
        category="smart",
        value="Long test PASSED",
        source="smartctl",
    )
)

print()

print("Observaciones")

for obs in disk.observations:
    print(
        obs.timestamp,
        obs.category,
        obs.value,
        obs.severity.name,
    )
disk.add_relationship(
    Relationship(
        source="debian-server",
        target="storage-wd-red-pro",
        type=RelationshipType.USES,
    )
)

print()

print("Relationships")

for rel in disk.relationships:
    print(
        rel.source,
        rel.type.name,
        rel.target,
    )
