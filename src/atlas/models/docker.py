from dataclasses import dataclass

from atlas.models.container import ContainerInfo


@dataclass(slots=True)
class DockerInfo:

    version: str

    total: int

    running: int

    exited: int

    containers: list[ContainerInfo]

    # Identity reported by the Docker daemon.
    # Optional for compatibility with historical snapshots.
    host_name: str | None = None

    # Provider availability is distinct from an empty inventory.
    # Historical snapshots default to available=True.
    available: bool = True

    error: str | None = None
