from atlas.services.assets.identity_reconciliation import (
    IdentityReconciliationService,
)


class FakeNetwork:
    def snapshot(
        self,
        *,
        active_scan=True,
    ):
        return {
            "status": "SUCCESS",
            "mode": "ACTIVE_LOCAL_SCAN",
            "gateway": {
                "ip": "192.168.1.1",
            },
            "local": {
                "cidr":
                    "192.168.1.208/24",
            },
            "devices": [
                {
                    "ip": "192.168.1.35",
                    "mac": "4c:eb:d6:ad:29:cf",
                    "name":
                        "LAN device 192.168.1.35",
                    "kind": "lan_device",
                    "source":
                        "kernel_neighbor_table",
                },
                {
                    "ip": "192.168.1.90",
                    "mac": "bc:24:11:03:32:57",
                    "name":
                        "LAN device 192.168.1.90",
                    "kind": "lan_device",
                    "source":
                        "kernel_neighbor_table",
                },
            ],
        }


class FakeHomeAssistant:
    def snapshot(self):
        return {
            "status": "SUCCESS",
            "summary": {
                "devices": 2,
            },
            "devices": [
                {
                    "id": "ha-reflector",
                    "name": "Reflector",
                    "system": False,
                    "ip": None,
                    "mac":
                        "4c:eb:d6:ad:29:cf",
                    "area": "Patio",
                    "manufacturer":
                        "SONOFF",
                    "model": "BASICR2",
                    "protocol":
                        "IP / SONOFF",
                    "category": "IoT",
                    "status": "ONLINE",
                    "entity_count": 6,
                },
                {
                    "id": "ha-zigbee",
                    "name":
                        "Monitor Homelab",
                    "system": False,
                    "ip": None,
                    "mac": None,
                    "protocol": "Zigbee",
                    "category": "Zigbee",
                },
            ],
        }


class FakeProxmox:
    def snapshot(self):
        return {
            "status": "SUCCESS",
            "guests": [
                {
                    "guest_type": "LXC",
                    "vmid": "102",
                    "name": "DB-Aceite",
                    "status": "running",
                    "mac":
                        "bc:24:11:03:32:57",
                    "ip":
                        "192.168.1.90",
                }
            ],
        }


def test_reconciliation_prefers_exact_mac_identity():
    service = (
        IdentityReconciliationService(
            network_service=
                FakeNetwork(),
            home_assistant_service=
                FakeHomeAssistant(),
            proxmox_service=
                FakeProxmox(),
        )
    )

    result = service.snapshot(
        active_scan=False
    )

    by_ip = {
        item["ip"]: item
        for item
        in result["devices"]
    }

    assert (
        by_ip["192.168.1.35"][
            "name"
        ]
        == "Reflector"
    )

    assert (
        by_ip["192.168.1.35"][
            "home_assistant"
        ]["area"]
        == "Patio"
    )

    assert (
        by_ip["192.168.1.90"][
            "name"
        ]
        == "DB-Aceite"
    )

    assert (
        by_ip["192.168.1.90"][
            "proxmox"
        ]["vmid"]
        == "102"
    )


def test_zigbee_device_is_not_falsely_added_to_lan():
    service = (
        IdentityReconciliationService(
            network_service=
                FakeNetwork(),
            home_assistant_service=
                FakeHomeAssistant(),
            proxmox_service=
                FakeProxmox(),
        )
    )

    result = service.snapshot(
        active_scan=False
    )

    names = {
        item["name"]
        for item
        in result["devices"]
    }

    assert (
        "Monitor Homelab"
        not in names
    )


def test_reconciliation_preserves_all_identity_sources():
    service = (
        IdentityReconciliationService(
            network_service=
                FakeNetwork(),
            home_assistant_service=
                FakeHomeAssistant(),
            proxmox_service=
                FakeProxmox(),
        )
    )

    result = service.snapshot(
        active_scan=False
    )

    by_ip = {
        item["ip"]: item
        for item
        in result["devices"]
    }

    reflector_sources = set(
        by_ip["192.168.1.35"][
            "sources"
        ]
    )

    db_sources = set(
        by_ip["192.168.1.90"][
            "sources"
        ]
    )

    assert (
        "kernel_neighbor_table"
        in reflector_sources
    )

    assert (
        "home_assistant"
        in reflector_sources
    )

    assert (
        "kernel_neighbor_table"
        in db_sources
    )

    assert (
        "proxmox"
        in db_sources
    )
