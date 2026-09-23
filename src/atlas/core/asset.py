from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum, auto
from .identity import AssetIdentity

class AssetType(Enum):
    SERVER = auto()
    VM = auto()
    LXC = auto()
    CONTAINER = auto()
    APPLICATION = auto()
    DATABASE = auto()
    STORAGE = auto()
    NETWORK = auto()
    SENSOR = auto()
    SERVICE = auto()




class ServiceRole(Enum):
    INFRASTRUCTURE = auto()
    CONTAINER_RUNTIME = auto()
    SYSTEM = auto()
    TIMER = auto()
    NETWORK = auto()
    STORAGE = auto()
    DATABASE = auto()
    MANAGEMENT = auto()
    MONITORING = auto()
    SECURITY = auto()
    UNKNOWN = auto()



class ServiceImportance(Enum):
    CRITICAL = auto()
    IMPORTANT = auto()
    NORMAL = auto()
    SYSTEM = auto()


class AssetRole(Enum):
    HYPERVISOR = auto()
    DOCKER_HOST = auto()
    APPLICATION_SERVER = auto()
    DATABASE_SERVER = auto()
    MONITORING_NODE = auto()
    HOME_AUTOMATION = auto()
    STORAGE_NODE = auto()
    MEDIA_SERVER = auto()
    SECURITY_NODE = auto()
    UTILITY_SERVICE = auto()
    CACHE_SERVICE = auto()
    AI_NODE = auto()
    UNKNOWN = auto()


class AssetStatus(Enum):
    ONLINE = auto()
    OFFLINE = auto()
    DEGRADED = auto()
    UNKNOWN = auto()


class AssetPresence(Enum):
    ACTIVE = auto()
    STALE = auto()
    RETIRED = auto()


def health_from_status(status: AssetStatus) -> float:
    """Translate operational status into baseline asset health.

    This is the baseline health only. More advanced health signals
    can be layered on top later (dependencies, resources, SMART,
    observations, errors, etc.).
    """

    values = {
        AssetStatus.ONLINE: 100.0,
        AssetStatus.DEGRADED: 40.0,
        AssetStatus.OFFLINE: 0.0,
        AssetStatus.UNKNOWN: 0.0,
    }

    return values[status]


class Criticality(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


class Capability(Enum):
    START = auto()
    STOP = auto()
    RESTART = auto()
    LOGS = auto()
    SMART = auto()
    TEMPERATURE = auto()
    SNAPSHOT = auto()
    BACKUP = auto()


@dataclass(slots=True)
class Asset:
    id: str
    name: str
    type: AssetType

    identity: AssetIdentity = field(
        default_factory=AssetIdentity
    )


    metadata: dict = field(
        default_factory=dict
    )
    status: AssetStatus = AssetStatus.UNKNOWN
    health: float = 0.0
    criticality: Criticality = Criticality.MEDIUM

    service_role: ServiceRole = ServiceRole.UNKNOWN

    service_importance: ServiceImportance = ServiceImportance.SYSTEM

    asset_roles: set[AssetRole] = field(
        default_factory=set
    )


    primary_role: AssetRole = AssetRole.UNKNOWN


    role_confidence: int = 0


    role_evidence: list[str] = field(
        default_factory=list
    )


    capabilities: set[Capability] = field(default_factory=set)
    observations: list = field(default_factory=list)
    relationships: list = field(default_factory=list)

    last_seen: datetime = field(default_factory=lambda: datetime.now(UTC))

    #
    # Inventory lifecycle is deliberately independent from
    # operational status.
    #
    # An asset can be OFFLINE while still ACTIVE inventory, and
    # a RETIRED asset preserves its last operational status.
    #
    presence: AssetPresence = AssetPresence.ACTIVE

    presence_changed_at: datetime | None = None


    def role_weight(self):
        """Return operational importance weight."""

        weights = {

            AssetRole.SECURITY_NODE: 90,

            AssetRole.HYPERVISOR: 90,

            AssetRole.DATABASE_SERVER: 85,

            AssetRole.MONITORING_NODE: 70,

            AssetRole.MEDIA_SERVER: 60,

            AssetRole.STORAGE_NODE: 60,

            AssetRole.APPLICATION_SERVER: 60,

            AssetRole.DOCKER_HOST: 80,

            AssetRole.UTILITY_SERVICE: 30,

            AssetRole.UNKNOWN: 10,

        }

        if not self.asset_roles:
            return 10

        return max(
            weights.get(
                role,
                10
            )
            for role in self.asset_roles
        )



    def is_online(self) -> bool:
        return self.status == AssetStatus.ONLINE

    def is_healthy(self) -> bool:
        return self.health >= 80.0

    def can(self, capability: Capability) -> bool:
        return capability in self.capabilities

    def add_capability(self, capability: Capability) -> None:
        self.capabilities.add(capability)

    def add_observation(self, observation) -> None:
        self.observations.append(observation)
        self.last_seen = datetime.now(UTC)

    def add_relationship(self, relationship) -> None:
        self.relationships.append(relationship)


    def explain_importance(self) -> dict:
        """Return a deterministic explanation of the asset's importance.

            The method simply reflects the values that were stored during
            classification.  It does **not** perform any inference or call out to
            other components.  The returned dictionary is JSON‑serialisable and
            contains the following keys:

            * ``service_role`` – the name of :class:`ServiceRole` enum value or
              ``None`` if unset.
            * ``service_importance`` – the name of :class:`ServiceImportance`
              enum value or ``None`` if unset.
            * ``reason`` – the raw classification reason stored in
              ``metadata['classification_reason']`` or ``None`` when missing.

            The method guarantees that calling it has no side‑effects on the
            asset instance.
            """
        role_name = self.service_role.name if self.service_role else None
        importance_name = self.service_importance.name if self.service_importance else None
        reason = self.metadata.get('classification_reason')
        return {'service_role': role_name, 'service_importance': importance_name, 'reason': reason}
