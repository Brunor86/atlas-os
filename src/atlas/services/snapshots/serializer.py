import json
from datetime import datetime, timezone

from atlas.core.version import __version__


SCHEMA_VERSION = 3


class SnapshotSerializer:


    def serialize(
        self,
        infra,
        health,
        insights,
        logs=None,
    ):

        data = {

            "metadata": {

                "atlas_version": __version__,

                "schema_version": SCHEMA_VERSION,

                "created_at":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),

            },


            "system": {

                "hostname": infra.system.hostname,

                "os_name": infra.system.os_name,

                "kernel": infra.system.kernel,

                "architecture": infra.system.architecture,

                "python_version": infra.system.python_version,

                "uptime": infra.system.uptime,

                "boot_time": infra.system.boot_time,

                "timezone": infra.system.timezone,

                "cpu_percent": infra.system.cpu_percent,

                "cpu_cores": infra.system.cpu_cores,

                "memory_percent": infra.system.memory_percent,

                "memory_used_gb": infra.system.memory_used_gb,

                "memory_total_gb": infra.system.memory_total_gb,

            },


            "docker": {

                "version": infra.docker.version,

                "total": infra.docker.total,

                "running": infra.docker.running,

                "exited": infra.docker.exited,

                "available":
                    getattr(
                        infra.docker,
                        "available",
                        True,
                    ),

                "error":
                    getattr(
                        infra.docker,
                        "error",
                        None,
                    ),

                "containers": [

                    {

                        "id": container.id,

                        "name": container.name,

                        "image": container.image,

                        "status": container.status,

                        "health": container.health,

                        "cpu_percent": container.cpu_percent,

                        "memory_mb": container.memory_mb,

                    }

                    for container in infra.docker.containers

                ],

            },


            "storage": [

                {

                    "filesystem": disk.filesystem,

                    "mountpoint": disk.mountpoint,

                    "total_gb": disk.total_gb,

                    "used_gb": disk.used_gb,

                    "free_gb": disk.free_gb,

                    "usage_percent": disk.usage_percent,

                }

                for disk in infra.storage

            ],


            "network": {

                "hostname": infra.network.hostname,

                "interfaces": [

                    {

                        "name": interface.name,

                        "address": interface.address,

                        "status": interface.status,

                    }

                    for interface in infra.network.interfaces

                ],

                "gateway": infra.network.gateway,

                "dns": infra.network.dns,

            },


            "proxmox": {

                "version": infra.proxmox.version,

                "release": infra.proxmox.release,

                "node": infra.proxmox.node,

                "available":
                    getattr(
                        infra.proxmox,
                        "available",
                        True,
                    ),

                "error":
                    getattr(
                        infra.proxmox,
                        "error",
                        None,
                    ),

                "guests": [

                    {

                        "vmid": guest.vmid,

                        "name": guest.name,

                        "type": guest.type,

                        "status": guest.status,

                        "memory": guest.memory,

                        "cpu": guest.cpu,

                    }

                    for guest in infra.proxmox.guests

                ],

            },


            "logs": logs or [],


            "health": health.status,


            "insights": [

                {

                    "title": item.title,

                    "summary": item.summary,

                    "severity": item.severity,

                }

                for item in insights

            ]

        }


        return json.dumps(
            data,
            indent=2
        )
