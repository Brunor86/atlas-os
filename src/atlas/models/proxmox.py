from dataclasses import dataclass


@dataclass
class ProxmoxGuest:

    vmid: int
    name: str
    type: str
    status: str

    memory: int
    max_memory: int

    cpu: float
    max_cpu: int

    disk: int
    max_disk: int

    disk_read: int
    disk_write: int

    net_in: int
    net_out: int

    uptime: int

    storage_devices: list[dict] | None = None


@dataclass(frozen=True)
class ProxmoxGuestRuntime:

    vmid: int
    name: str
    type: str
    node: str
    status: str


@dataclass
class ProxmoxNode:

    node: str
    status: str

    memory: int
    max_memory: int

    cpu: float
    max_cpu: int

    disk: int
    max_disk: int

    uptime: int

    storage_devices: list[dict] | None = None


@dataclass
class ProxmoxInfo:

    version: str
    release: str
    node: str

    node_info: ProxmoxNode | None

    guests: list[ProxmoxGuest]

    # Provider availability is distinct from zero discovered guests.
    # Historical snapshots default to available=True.
    available: bool = True

    error: str | None = None
