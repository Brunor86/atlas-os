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
        "type": "qemu",
        "vmid": 300,
        "name": "atlas-windows",
        "node": "atlas",
        "status": "stopped",
    },
]


CONFIG_200 = {
    "hostpci0":
        "0000:01:00.0",
    "hostpci1":
        "0000:01:00.1",
}


CONFIG_300 = {
    "hostpci0":
        "0000:01:00.0,pcie=1",
    "hostpci1":
        "0000:01:00.1,pcie=1",
}


def fake_service(
    resources=None,
):

    service = ProxmoxService.__new__(
        ProxmoxService
    )

    selected = (
        resources
        if resources is not None
        else RESOURCES
    )

    def fake_get(
        endpoint,
    ):

        if endpoint == (
            "/api2/json/"
            "cluster/resources?type=vm"
        ):
            return selected

        if endpoint == (
            "/api2/json/nodes/"
            "atlas/qemu/200/config"
        ):
            return CONFIG_200

        if endpoint == (
            "/api2/json/nodes/"
            "atlas/qemu/300/config"
        ):
            return CONFIG_300

        raise AssertionError(
            "unexpected endpoint: "
            + endpoint
        )

    service._get = fake_get

    return service


def test_extract_hostpci_devices():

    assert (
        ProxmoxService
        ._hostpci_devices_from_config(
            CONFIG_300
        )
        == {
            "0000:01:00.0",
            "0000:01:00.1",
        }
    )


def test_extract_hostpci_without_domain():

    assert (
        ProxmoxService
        ._hostpci_devices_from_config(
            {
                "hostpci0":
                    "01:00.0,pcie=1",
            }
        )
        == {
            "0000:01:00.0",
        }
    )


def test_qemu_pci_devices():

    service = fake_service()

    assert service.qemu_pci_devices(
        300
    ) == [
        "0000:01:00.0",
        "0000:01:00.1",
    ]


def test_running_qemu_pci_conflict_detected():

    service = fake_service()

    conflicts = (
        service
        .running_qemu_pci_conflicts(
            300
        )
    )

    assert conflicts == [
        {
            "vmid": 200,
            "name": "atlas-ai",
            "node": "atlas",
            "devices": [
                "0000:01:00.0",
                "0000:01:00.1",
            ],
        }
    ]


def test_stopped_vm_is_not_conflict():

    resources = [
        {
            **RESOURCES[0],
            "status": "stopped",
        },
        RESOURCES[1],
    ]

    service = fake_service(
        resources
    )

    assert (
        service
        .running_qemu_pci_conflicts(
            300
        )
        == []
    )


def test_vm_without_hostpci_has_no_conflict():

    service = fake_service()

    original_get = service._get

    def fake_get(
        endpoint,
    ):

        if endpoint == (
            "/api2/json/nodes/"
            "atlas/qemu/300/config"
        ):
            return {
                "memory": 8192,
            }

        return original_get(
            endpoint
        )

    service._get = fake_get

    assert (
        service
        .running_qemu_pci_conflicts(
            300
        )
        == []
    )
