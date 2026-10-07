from atlas.services.assets.home_assistant_discovery import (
    HomeAssistantDiscoveryService,
)


def test_home_assistant_snapshot_groups_real_devices():
    service = (
        HomeAssistantDiscoveryService()
    )

    raw = {
        "areas": [
            {
                "area_id": "living",
                "name": "Living Room",
            }
        ],
        "devices": [
            {
                "id": "zigbee-1",
                "name": "Monitor Homelab",
                "name_by_user": None,
                "area_id": "living",
                "manufacturer": "SONOFF",
                "model": "TS011F",
                "connections": [
                    [
                        "mac",
                        "AA:BB:CC:DD:EE:FF",
                    ]
                ],
                "identifiers": [
                    [
                        "zha",
                        "00:12:4b:00:11:22:33:44",
                    ]
                ],
            },
            {
                "id": "generic-1",
                "name": "192_168_1_135",
                "area_id": "living",
                "manufacturer": "Generic",
                "model": None,
                "connections": [],
                "identifiers": [],
            },
            {
                "id": "ha-core",
                "name": "Home Assistant Core",
                "area_id": None,
                "manufacturer":
                    "Home Assistant",
                "model":
                    "Home Assistant Core",
                "connections": [],
                "identifiers": [],
            },
        ],
        "entities": [
            {
                "entity_id":
                    "switch.monitor_homelab",
                "device_id":
                    "zigbee-1",
                "platform":
                    "zha",
            },
            {
                "entity_id":
                    "sensor.generic",
                "device_id":
                    "generic-1",
                "platform":
                    "generic",
            },
            {
                "entity_id":
                    "sensor.core_version",
                "device_id":
                    "ha-core",
                "platform":
                    "hassio",
            },
        ],
        "states": [
            {
                "entity_id":
                    "switch.monitor_homelab",
                "state":
                    "on",
                "attributes": {},
            },
            {
                "entity_id":
                    "sensor.generic",
                "state":
                    "on",
                "attributes": {},
            },
            {
                "entity_id":
                    "sensor.core_version",
                "state":
                    "2026.10",
                "attributes": {},
            },
        ],
    }

    result = (
        service._build_snapshot(
            raw,
            generated_at=
                "2026-10-07T00:00:00+00:00",
            instance_url=
                "http://homeassistant:8123",
        )
    )

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert (
        result["summary"]["devices"]
        == 3
    )

    assert (
        result["summary"][
            "zigbee_devices"
        ]
        == 1
    )

    by_id = {
        item["id"]: item
        for item
        in result["devices"]
    }

    assert (
        by_id["zigbee-1"][
            "protocol"
        ]
        == "Zigbee"
    )

    assert (
        by_id["zigbee-1"]["ieee"]
        == "00:12:4b:00:11:22:33:44"
    )

    assert (
        by_id["zigbee-1"]["mac"]
        == "aa:bb:cc:dd:ee:ff"
    )

    assert (
        by_id["generic-1"]["ip"]
        == "192.168.1.135"
    )

    assert (
        by_id["ha-core"]["system"]
        is True
    )


def test_snapshot_does_not_require_or_expose_token():
    service = (
        HomeAssistantDiscoveryService()
    )

    result = (
        service._build_snapshot(
            {
                "areas": [],
                "devices": [],
                "entities": [],
                "states": [],
            },
            generated_at=
                "2026-10-07T00:00:00+00:00",
            instance_url=
                "http://homeassistant:8123",
        )
    )

    rendered = str(result)

    assert "HA_TOKEN" not in rendered
    assert "access_token" not in rendered


def test_home_assistant_normalizes_invisible_display_name():
    service = (
        HomeAssistantDiscoveryService()
    )

    raw = {
        "areas": [],
        "devices": [
            {
                "id": "device-1",
                "name":
                    "\u200bReflector\u00a0",
                "name_by_user": None,
                "area_id": None,
                "connections": [],
                "identifiers": [],
            }
        ],
        "entities": [],
        "states": [],
    }

    result = (
        service._build_snapshot(
            raw,
            generated_at=
                "2026-10-07T00:00:00+00:00",
            instance_url=
                "http://homeassistant:8123",
        )
    )

    assert (
        result["devices"][0]["name"]
        == "Reflector"
    )
