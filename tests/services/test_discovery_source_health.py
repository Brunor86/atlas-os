from types import SimpleNamespace

import pytest

import atlas.providers.storage as storage_module
import atlas.collectors.services.systemd as systemd_module
import atlas.collectors.services.lxc as lxc_module

from atlas.providers.storage import (
    StorageAssetProvider,
)

from atlas.collectors.services.systemd import (
    SystemdServiceCollector,
)

from atlas.collectors.services.lxc import (
    LXCServiceCollector,
)


class EmptyTelemetry:

    def block_devices(
        self,
    ):

        return []


def test_storage_provider_reports_remote_inventory_failure(
    monkeypatch,
):

    monkeypatch.setattr(
        storage_module,
        "is_proxmox_configured",
        lambda:
            True,
    )

    def fail_host():

        raise RuntimeError(
            "missing proxmox host"
        )

    monkeypatch.setattr(
        storage_module,
        "require_proxmox_host",
        fail_host,
    )

    provider = StorageAssetProvider(
        telemetry=EmptyTelemetry()
    )

    assets = (
        provider.collect()
    )

    assert assets == []

    assert provider.errors == [
        (
            "Proxmox SMART: "
            "missing proxmox host"
        )
    ]


def test_storage_provider_resets_errors_each_cycle(
    monkeypatch,
):

    monkeypatch.setattr(
        storage_module,
        "is_proxmox_configured",
        lambda:
            True,
    )

    calls = {
        "count": 0,
    }

    def host():

        calls["count"] += 1

        if calls["count"] == 1:

            raise RuntimeError(
                "temporary failure"
            )

        return "proxmox"

    class EmptySmartCollector:

        def __init__(
            self,
            host,
            device,
        ):
            self.host = host
            self.device = device

        def collect(
            self,
        ):
            return []

    monkeypatch.setattr(
        storage_module,
        "require_proxmox_host",
        host,
    )

    monkeypatch.setattr(
        storage_module,
        "ProxmoxSmartCollector",
        EmptySmartCollector,
    )

    provider = StorageAssetProvider(
        telemetry=EmptyTelemetry()
    )

    provider.collect()

    assert len(
        provider.errors
    ) == 1

    provider.collect()

    assert (
        provider.errors
        == []
    )


def test_systemd_service_collector_raises_on_command_failure(
    monkeypatch,
):

    def fake_run(
        *args,
        **kwargs,
    ):

        return SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="systemctl unavailable",
        )

    monkeypatch.setattr(
        systemd_module.subprocess,
        "run",
        fake_run,
    )

    collector = (
        SystemdServiceCollector()
    )

    with pytest.raises(
        RuntimeError,
        match="systemctl unavailable",
    ):

        collector.collect()


def test_lxc_service_collector_raises_on_ssh_failure(
    monkeypatch,
):

    def fake_run(
        *args,
        **kwargs,
    ):

        return SimpleNamespace(
            returncode=255,
            stdout="",
            stderr="ssh unavailable",
        )

    monkeypatch.setattr(
        lxc_module.subprocess,
        "run",
        fake_run,
    )

    collector = LXCServiceCollector(
        proxmox_host="proxmox"
    )

    with pytest.raises(
        RuntimeError,
        match="ssh unavailable",
    ):

        collector.collect(
            {
                "vmid": 103,
                "hostname": "olivasat",
                "type": "LXC",
            }
        )


def test_proxmox_smart_collector_raises_on_ssh_transport_failure(
    monkeypatch,
):

    from atlas.collectors.proxmox import smart as smart_module

    def fake_run(
        *args,
        **kwargs,
    ):

        return SimpleNamespace(
            returncode=255,
            stdout="",
            stderr="ssh: connect to host failed",
        )

    monkeypatch.setattr(
        smart_module.subprocess,
        "run",
        fake_run,
    )

    collector = (
        smart_module.ProxmoxSmartCollector(
            "proxmox",
            "/dev/sda",
        )
    )

    with pytest.raises(
        RuntimeError,
        match="Proxmox SMART SSH failed",
    ):

        collector.collect()


def test_proxmox_smart_collector_raises_when_identity_is_missing(
    monkeypatch,
):

    from atlas.collectors.proxmox import smart as smart_module

    def fake_run(
        *args,
        **kwargs,
    ):

        return SimpleNamespace(
            returncode=127,
            stdout="",
            stderr="smartctl: command not found",
        )

    monkeypatch.setattr(
        smart_module.subprocess,
        "run",
        fake_run,
    )

    collector = (
        smart_module.ProxmoxSmartCollector(
            "proxmox",
            "/dev/sda",
        )
    )

    with pytest.raises(
        RuntimeError,
        match="Proxmox SMART unavailable",
    ):

        collector.collect()


def test_proxmox_smart_collector_accepts_diagnostic_nonzero_status(
    monkeypatch,
):

    from atlas.collectors.proxmox import smart as smart_module

    output = """
Device Model:     WDC WD120EFGX-68CPHN0
Serial Number:    WD-B00YPVHD
Firmware Version: 85.00A85
SMART overall-health self-assessment test result: PASSED
"""

    def fake_run(
        *args,
        **kwargs,
    ):

        #
        # Non-zero smartctl diagnostic status must not be confused
        # with an SSH / inventory failure.
        #
        return SimpleNamespace(
            returncode=8,
            stdout=output,
            stderr="",
        )

    monkeypatch.setattr(
        smart_module.subprocess,
        "run",
        fake_run,
    )

    collector = (
        smart_module.ProxmoxSmartCollector(
            "proxmox",
            "/dev/sda",
        )
    )

    result = collector.collect()

    assert len(result) == 1

    smart = result[0]

    assert (
        smart.model
        == "WDC WD120EFGX-68CPHN0"
    )

    assert (
        smart.serial
        == "WD-B00YPVHD"
    )

    assert smart.smart_available is True
    assert smart.smart_passed is True


def test_storage_provider_skips_unconfigured_proxmox_smart(
    monkeypatch,
):

    monkeypatch.setattr(
        storage_module,
        "is_proxmox_configured",
        lambda:
            False,
        raising=False,
    )

    def should_not_run():

        raise AssertionError(
            "unconfigured Proxmox SMART must be skipped"
        )

    monkeypatch.setattr(
        storage_module,
        "require_proxmox_host",
        should_not_run,
    )

    provider = StorageAssetProvider(
        telemetry=EmptyTelemetry()
    )

    assets = provider.collect()

    assert assets == []
    assert provider.errors == []
