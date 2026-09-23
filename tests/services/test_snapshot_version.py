import json
from types import SimpleNamespace

from atlas.core.version import __version__
from atlas.models.docker import DockerInfo
from atlas.models.proxmox import ProxmoxInfo
from atlas.services.snapshots.serializer import (
    SnapshotSerializer,
)


def test_snapshot_uses_runtime_atlas_version():

    infra = SimpleNamespace(

        system=SimpleNamespace(
            hostname="test",
            os_name="test",
            kernel="test",
            architecture="x86_64",
            python_version="3",
            uptime=0,
            boot_time="test",
            timezone="UTC",
            cpu_percent=0,
            cpu_cores=1,
            memory_percent=0,
            memory_used_gb=0,
            memory_total_gb=1,
        ),

        docker=DockerInfo(
            version="test",
            total=0,
            running=0,
            exited=0,
            containers=[],
        ),

        storage=[],

        network=SimpleNamespace(
            hostname="test",
            interfaces=[],
            gateway=None,
            dns=[],
        ),

        proxmox=ProxmoxInfo(
            version="test",
            release="test",
            node="atlas",
            node_info=None,
            guests=[],
        ),
    )


    payload = json.loads(
        SnapshotSerializer().serialize(
            infra,
            SimpleNamespace(
                status="healthy"
            ),
            [],
        )
    )


    assert (
        payload["metadata"]["atlas_version"]
        == __version__
    )

    assert (
        payload["metadata"]["schema_version"]
        == 3
    )
