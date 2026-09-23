import json
from types import SimpleNamespace

import pytest

from atlas.models.docker import DockerInfo
from atlas.models.proxmox import ProxmoxInfo


def _service(
    value,
):

    return lambda: SimpleNamespace(
        get_info=lambda:
            value
    )


def _install_good_local_services(
    monkeypatch,
    module,
):

    monkeypatch.setattr(
        module,
        "SystemService",
        _service(
            SimpleNamespace(
                name="system"
            )
        ),
    )

    monkeypatch.setattr(
        module,
        "StorageService",
        _service(
            []
        ),
    )

    monkeypatch.setattr(
        module,
        "NetworkService",
        _service(
            SimpleNamespace(
                name="network"
            )
        ),
    )


def _healthy_docker():

    return DockerInfo(
        version="test",
        total=1,
        running=1,
        exited=0,
        containers=[],
        host_name="test-host",
    )


def _healthy_proxmox():

    return ProxmoxInfo(
        version="test",
        release="test",
        node="test-node",
        node_info=None,
        guests=[],
    )


def test_docker_failure_is_isolated(
    monkeypatch,
):

    import atlas.services.infrastructure as module

    _install_good_local_services(
        monkeypatch,
        module,
    )

    def unavailable():
        raise RuntimeError(
            "synthetic docker outage"
        )

    proxmox = _healthy_proxmox()

    monkeypatch.setattr(
        module,
        "DockerService",
        unavailable,
    )

    monkeypatch.setattr(
        module,
        "ProxmoxService",
        _service(
            proxmox
        ),
    )


    infra = (
        module.InfrastructureService()
        .collect()
    )


    assert infra.docker.available is False

    assert infra.docker.total == 0

    assert (
        "synthetic docker outage"
        in infra.docker.error
    )

    assert infra.proxmox is proxmox


def test_proxmox_failure_is_isolated(
    monkeypatch,
):

    import atlas.services.infrastructure as module

    _install_good_local_services(
        monkeypatch,
        module,
    )

    docker = _healthy_docker()

    def unavailable():
        raise RuntimeError(
            "synthetic proxmox outage"
        )

    monkeypatch.setattr(
        module,
        "DockerService",
        _service(
            docker
        ),
    )

    monkeypatch.setattr(
        module,
        "ProxmoxService",
        unavailable,
    )


    infra = (
        module.InfrastructureService()
        .collect()
    )


    assert infra.docker is docker

    assert infra.proxmox.available is False

    assert infra.proxmox.guests == []

    assert (
        "synthetic proxmox outage"
        in infra.proxmox.error
    )


def test_local_host_provider_failure_remains_fail_closed(
    monkeypatch,
):

    import atlas.services.infrastructure as module


    def failed_system():
        raise RuntimeError(
            "synthetic local system failure"
        )


    monkeypatch.setattr(
        module,
        "SystemService",
        failed_system,
    )

    monkeypatch.setattr(
        module,
        "StorageService",
        _service([]),
    )

    monkeypatch.setattr(
        module,
        "NetworkService",
        _service(
            SimpleNamespace()
        ),
    )

    monkeypatch.setattr(
        module,
        "DockerService",
        _service(
            _healthy_docker()
        ),
    )

    monkeypatch.setattr(
        module,
        "ProxmoxService",
        _service(
            _healthy_proxmox()
        ),
    )


    with pytest.raises(
        RuntimeError,
        match=(
            "synthetic local "
            "system failure"
        ),
    ):

        (
            module.InfrastructureService()
            .collect()
        )


def test_docker_unavailable_marks_health_warning():

    from atlas.services.health.service import (
        HealthService,
    )


    infra = SimpleNamespace(
        docker=DockerInfo(
            version="unavailable",
            total=0,
            running=0,
            exited=0,
            containers=[],
            available=False,
            error="Docker daemon unavailable",
        ),

        proxmox=_healthy_proxmox(),
    )


    health = (
        HealthService()
        .evaluate(
            infra
        )
    )


    assert health.status == "warning"

    assert any(
        alert.title
        == "Docker unavailable"

        for alert
        in health.alerts
    )


def test_proxmox_unavailable_marks_health_warning():

    from atlas.services.health.service import (
        HealthService,
    )


    infra = SimpleNamespace(
        docker=_healthy_docker(),

        proxmox=ProxmoxInfo(
            version="unavailable",
            release="",
            node="unknown",
            node_info=None,
            guests=[],
            available=False,
            error="synthetic Proxmox outage",
        ),
    )


    health = (
        HealthService()
        .evaluate(
            infra
        )
    )


    assert health.status == "warning"

    assert any(
        alert.title
        == "Proxmox unavailable"

        for alert
        in health.alerts
    )


def _snapshot_infrastructure():

    system = SimpleNamespace(
        hostname="test-host",
        os_name="test-os",
        kernel="test-kernel",
        architecture="x86_64",
        python_version="3",
        uptime=1,
        boot_time="test",
        timezone="UTC",
        cpu_percent=0,
        cpu_cores=1,
        memory_percent=0,
        memory_used_gb=0,
        memory_total_gb=1,
    )

    network = SimpleNamespace(
        hostname="test-host",
        interfaces=[],
        gateway=None,
        dns=[],
    )

    return SimpleNamespace(
        system=system,

        docker=DockerInfo(
            version="unavailable",
            total=0,
            running=0,
            exited=0,
            containers=[],
            available=False,
            error="docker unavailable",
        ),

        storage=[],

        network=network,

        proxmox=ProxmoxInfo(
            version="unavailable",
            release="",
            node="unknown",
            node_info=None,
            guests=[],
            available=False,
            error="proxmox unavailable",
        ),
    )


def test_snapshot_persists_provider_availability():

    from atlas.services.snapshots.serializer import (
        SnapshotSerializer,
    )


    payload = json.loads(
        SnapshotSerializer().serialize(
            _snapshot_infrastructure(),
            SimpleNamespace(
                status="warning"
            ),
            [],
        )
    )


    assert (
        payload["metadata"][
            "schema_version"
        ]
        == 3
    )

    assert (
        payload["docker"][
            "available"
        ]
        is False
    )

    assert (
        payload["docker"][
            "error"
        ]
        == "docker unavailable"
    )

    assert (
        payload["proxmox"][
            "available"
        ]
        is False
    )

    assert (
        payload["proxmox"][
            "error"
        ]
        == "proxmox unavailable"
    )


def test_historical_snapshot_defaults_to_available(
    monkeypatch,
):

    import atlas.services.snapshots.loader as module


    old = {
        "system": {
            "hostname": "test-host",
            "os_name": "test-os",
            "kernel": "test-kernel",
            "architecture": "x86_64",
            "python_version": "3",
            "uptime": 1,
            "boot_time": "test",
            "timezone": "UTC",
            "cpu_percent": 0,
            "cpu_cores": 1,
            "memory_percent": 0,
            "memory_used_gb": 0,
            "memory_total_gb": 1,
        },

        "docker": {
            "version": "historical",
            "total": 0,
            "running": 0,
            "exited": 0,
            "containers": [],
        },

        "storage": [],

        "network": {
            "hostname": "test-host",
            "interfaces": [],
            "gateway": None,
            "dns": [],
        },

        "proxmox": {
            "version": "historical",
            "release": "",
            "node": "atlas",
            "guests": [],
        },
    }


    class FakeDatabase:

        def get_last_snapshot(
            self,
        ):

            return (
                "historical",
                json.dumps(
                    old
                ),
            )


    monkeypatch.setattr(
        module,
        "Database",
        FakeDatabase,
    )


    infra = (
        module.SnapshotLoader()
        .load()
    )


    assert infra.docker.available is True

    assert infra.docker.error is None

    assert infra.proxmox.available is True

    assert infra.proxmox.error is None


def test_ai_provider_unavailable_reports_offline(
    monkeypatch,
):

    from atlas.services.ai.health import (
        AIRuntimeHealth,
    )

    from atlas.services.ai.llm.ollama import (
        OllamaProvider,
    )


    monkeypatch.setattr(
        OllamaProvider,
        "available",
        lambda self:
            False,
    )


    runtime = SimpleNamespace(
        status=lambda:
            []
    )

    target = SimpleNamespace(
        name="test-ai",
        provider="ollama",
        url="ollama://127.0.0.1:1",
        host="127.0.0.1",
        port=1,
        enabled=True,
    )


    status = (
        AIRuntimeHealth(
            runtime,
            target,
        )
        .status()
    )


    assert status["status"] == "OFFLINE"

    assert (
        status[
            "provider_available"
        ]
        is False
    )
