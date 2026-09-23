import json

from atlas.core.infrastructure import Infrastructure

from atlas.models.system import SystemInfo
from atlas.models.docker import DockerInfo
from atlas.models.container import ContainerInfo
from atlas.models.storage import StorageInfo
from atlas.models.network import NetworkInfo, NetworkInterface
from atlas.models.proxmox import ProxmoxInfo, ProxmoxGuest

from atlas.storage.database import Database


class SnapshotLoader:


    def __init__(self):

        self.database = Database()


    def load(self):

        snapshot = self.database.get_last_snapshot()

        if not snapshot:
            return None


        created_at, data = snapshot

        data = json.loads(data)


        system = SystemInfo(
            **data["system"]
        )


        containers = [

            ContainerInfo(
                **container
            )

            for container in data["docker"]["containers"]

        ]


        docker = DockerInfo(

            version=data["docker"]["version"],

            total=data["docker"]["total"],

            running=data["docker"]["running"],

            exited=data["docker"]["exited"],

            containers=containers,

            available=(
                data["docker"].get(
                    "available",
                    True,
                )
            ),

            error=(
                data["docker"].get(
                    "error"
                )
            ),

        )


        storage = [

            StorageInfo(
                **disk
            )

            for disk in data["storage"]

        ]


        interfaces = [

            NetworkInterface(
                **interface
            )

            for interface in data["network"]["interfaces"]

        ]


        network = NetworkInfo(

            hostname=data["network"]["hostname"],

            interfaces=interfaces,

            gateway=data["network"]["gateway"],

            dns=data["network"]["dns"],

        )


        guests = []

        for guest in data["proxmox"]["guests"]:

            guests.append(
                ProxmoxGuest(
                    vmid=int(guest.get("vmid", 0)),
                    name=guest.get(
                        "name",
                        f"guest-{guest.get('vmid', 0)}",
                    ),
                    type=guest.get("type", "unknown"),
                    status=guest.get("status", "unknown"),

                    memory=int(
                        guest.get("memory", 0)
                    ),
                    max_memory=int(
                        guest.get("max_memory", 0)
                    ),

                    cpu=float(
                        guest.get("cpu", 0)
                    ),
                    max_cpu=int(
                        guest.get("max_cpu", 0)
                    ),

                    disk=int(
                        guest.get("disk", 0)
                    ),
                    max_disk=int(
                        guest.get("max_disk", 0)
                    ),

                    disk_read=int(
                        guest.get("disk_read", 0)
                    ),
                    disk_write=int(
                        guest.get("disk_write", 0)
                    ),

                    net_in=int(
                        guest.get("net_in", 0)
                    ),
                    net_out=int(
                        guest.get("net_out", 0)
                    ),

                    uptime=int(
                        guest.get("uptime", 0)
                    ),

                    storage_devices=guest.get(
                        "storage_devices",
                        [],
                    ),
                )
            )


        proxmox = ProxmoxInfo(

            version=data["proxmox"]["version"],

            release=data["proxmox"]["release"],

            node=data["proxmox"]["node"],

            node_info=data["proxmox"].get(
                "node_info"
            ),

            guests=guests,

            available=(
                data["proxmox"].get(
                    "available",
                    True,
                )
            ),

            error=(
                data["proxmox"].get(
                    "error"
                )
            ),

        )


        return Infrastructure(

            system=system,

            docker=docker,

            storage=storage,

            network=network,

            proxmox=proxmox,

        )
