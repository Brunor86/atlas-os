import pytest

from atlas.services.proxmox import (
    ProxmoxService,
)


RESOURCES = [
    {
        "type": "qemu",
        "vmid": 200,
        "name": "atlas-ai",
        "node": "atlas",
        "status": "running",
    },
    {
        "type": "lxc",
        "vmid": 103,
        "name": "olivasat",
        "node": "atlas",
        "status": "running",
    },
    {
        "type": "qemu",
        "vmid": 300,
        "name": "atlas-windows",
        "node": "atlas",
        "status": "stopped",
    },
]


def service():

    proxmox = object.__new__(
        ProxmoxService
    )

    def fake_get(endpoint):

        assert (
            endpoint
            == "/api2/json/cluster/resources?type=vm"
        )

        return RESOURCES

    proxmox._get = fake_get

    return proxmox


def test_resolve_qemu_guest():

    guest = service().resolve_guest(
        200,
        expected_type="qemu",
    )

    assert guest.vmid == 200
    assert guest.name == "atlas-ai"
    assert guest.type == "qemu"
    assert guest.node == "atlas"
    assert guest.status == "running"


def test_resolve_lxc_guest():

    guest = service().resolve_guest(
        103,
        expected_type="lxc",
    )

    assert guest.vmid == 103
    assert guest.name == "olivasat"
    assert guest.type == "lxc"
    assert guest.node == "atlas"
    assert guest.status == "running"


def test_resolve_stopped_guest():

    guest = service().resolve_guest(
        300,
        expected_type="qemu",
    )

    assert guest.status == "stopped"


def test_reject_wrong_guest_type():

    with pytest.raises(
        ValueError,
        match="is qemu, not lxc",
    ):

        service().resolve_guest(
            200,
            expected_type="lxc",
        )


def test_reject_unknown_vmid():

    with pytest.raises(
        LookupError,
        match="999",
    ):

        service().resolve_guest(
            999,
            expected_type="qemu",
        )


def test_reject_invalid_vmid():

    with pytest.raises(
        ValueError,
        match="invalid Proxmox VMID",
    ):

        service().resolve_guest(
            0,
        )
