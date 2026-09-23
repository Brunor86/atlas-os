from dataclasses import dataclass

from atlas.models.system import SystemInfo
from atlas.models.docker import DockerInfo
from atlas.models.network import NetworkInfo
from atlas.models.proxmox import ProxmoxInfo
from atlas.models.storage import StorageInfo


@dataclass(slots=True)
class Infrastructure:

    system: SystemInfo

    docker: DockerInfo

    network: NetworkInfo

    storage: list[StorageInfo]

    proxmox: ProxmoxInfo
