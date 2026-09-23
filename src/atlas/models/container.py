from dataclasses import dataclass


@dataclass(slots=True)
class ContainerInfo:

    id: str

    name: str

    image: str

    status: str

    health: str | None

    cpu_percent: float

    memory_mb: float

    # Docker runtime metadata.
    #
    # Defaults preserve compatibility with historical snapshots that
    # only contain the original ContainerInfo fields.
    labels: dict | None = None

    networks: list[str] | None = None

    mounts: list[dict] | None = None

    compose_project: str | None = None

    compose_service: str | None = None
