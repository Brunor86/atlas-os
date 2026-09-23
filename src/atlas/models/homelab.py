from dataclasses import dataclass, field

from atlas.models.system import SystemInfo


@dataclass(slots=True)
class Homelab:
    """
    Representa el estado completo del homelab.
    """

    system: SystemInfo

    hardware: object | None = None

    storage: list = field(default_factory=list)

    containers: list = field(default_factory=list)

    services: list = field(default_factory=list)

    networks: list = field(default_factory=list)
