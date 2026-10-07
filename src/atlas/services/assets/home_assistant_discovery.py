from __future__ import annotations

import asyncio
import html
import ipaddress
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import websockets


class HomeAssistantDiscoveryService:
    """
    Read-only Home Assistant registry observer.

    Reads:
    - device registry
    - entity registry
    - area registry
    - live entity states

    It never calls Home Assistant service/action endpoints.
    """

    ENV_PATH = Path(
        "/etc/atlas/homeassistant.env"
    )

    SYSTEM_INTEGRATIONS = {
        "backup",
        "hacs",
        "hassio",
        "google_translate",
        "met",
        "person",
        "shopping_list",
        "sun",
    }

    def snapshot(self) -> dict:
        generated_at = datetime.now(
            UTC
        ).isoformat()

        try:
            config = self._load_config()

            raw = asyncio.run(
                self._collect(
                    config["HA_URL"],
                    config["HA_TOKEN"],
                )
            )

            return self._build_snapshot(
                raw,
                generated_at=generated_at,
                instance_url=
                    config["HA_URL"],
            )

        except FileNotFoundError:
            return {
                "status":
                    "NOT_CONFIGURED",
                "generated_at":
                    generated_at,
                "error":
                    "Home Assistant credential file not found",
                "summary": {},
                "areas": [],
                "devices": [],
            }

        except Exception as exc:
            return {
                "status":
                    "ERROR",
                "generated_at":
                    generated_at,
                "error":
                    str(exc),
                "summary": {},
                "areas": [],
                "devices": [],
            }

    def _load_config(self) -> dict:
        values = {}

        for raw in (
            self.ENV_PATH
            .read_text()
            .splitlines()
        ):
            line = raw.strip()

            if (
                not line
                or line.startswith("#")
                or "=" not in line
            ):
                continue

            key, value = line.split(
                "=",
                1,
            )

            values[key] = value

        url = (
            values.get("HA_URL")
            or ""
        ).strip()

        token = (
            values.get("HA_TOKEN")
            or ""
        ).strip()

        if not url:
            raise RuntimeError(
                "HA_URL is not configured"
            )

        if not token:
            raise RuntimeError(
                "HA_TOKEN is not configured"
            )

        return {
            "HA_URL": url.rstrip("/"),
            "HA_TOKEN": token,
        }

    async def _collect(
        self,
        url: str,
        token: str,
    ):
        ws_url = self._websocket_url(
            url
        )

        async with websockets.connect(
            ws_url,
            open_timeout=5,
            close_timeout=2,
            max_size=32 * 1024 * 1024,
        ) as ws:

            hello = await self._recv(
                ws
            )

            if (
                hello.get("type")
                != "auth_required"
            ):
                raise RuntimeError(
                    "unexpected Home Assistant websocket handshake"
                )

            await ws.send(
                json.dumps(
                    {
                        "type": "auth",
                        "access_token":
                            token,
                    }
                )
            )

            auth = await self._recv(
                ws
            )

            if (
                auth.get("type")
                != "auth_ok"
            ):
                raise RuntimeError(
                    "Home Assistant websocket authentication failed"
                )

            devices = await self._command(
                ws,
                1,
                "config/device_registry/list",
            )

            entities = await self._command(
                ws,
                2,
                "config/entity_registry/list",
            )

            areas = await self._command(
                ws,
                3,
                "config/area_registry/list",
            )

            states = await self._command(
                ws,
                4,
                "get_states",
            )

        return {
            "devices": devices or [],
            "entities": entities or [],
            "areas": areas or [],
            "states": states or [],
        }

    async def _recv(self, ws):
        raw = await asyncio.wait_for(
            ws.recv(),
            timeout=10,
        )

        return json.loads(raw)

    async def _command(
        self,
        ws,
        command_id,
        command_type,
    ):
        await ws.send(
            json.dumps(
                {
                    "id": command_id,
                    "type": command_type,
                }
            )
        )

        while True:
            message = await self._recv(
                ws
            )

            if (
                message.get("id")
                != command_id
            ):
                continue

            if not message.get(
                "success",
                False,
            ):
                raise RuntimeError(
                    f"{command_type} failed"
                )

            return message.get(
                "result"
            )

    def _build_snapshot(
        self,
        raw,
        *,
        generated_at,
        instance_url,
    ):
        devices = raw.get(
            "devices",
            [],
        )

        entities = raw.get(
            "entities",
            [],
        )

        areas = raw.get(
            "areas",
            [],
        )

        states = raw.get(
            "states",
            [],
        )

        area_by_id = {
            (
                area.get("area_id")
                or area.get("id")
            ):
                area.get("name")
                or "Unnamed area"

            for area in areas
        }

        device_by_id = {
            device.get("id"):
                device

            for device in devices
            if device.get("id")
        }

        entities_by_device = (
            defaultdict(list)
        )

        for entity in entities:
            device_id = (
                entity.get(
                    "device_id"
                )
            )

            if device_id:
                entities_by_device[
                    device_id
                ].append(entity)

        states_by_id = {
            state.get("entity_id"):
                state

            for state in states
            if state.get("entity_id")
        }

        output = []

        for device in devices:

            device_id = (
                device.get("id")
            )

            if not device_id:
                continue

            name = self._clean_name(
                device.get(
                    "name_by_user"
                )
                or device.get(
                    "name"
                )
                or device_id
            )

            area_id = (
                device.get("area_id")
            )

            parent_id = (
                device.get(
                    "parent_device_id"
                )
            )

            if (
                not area_id
                and parent_id
            ):
                parent = (
                    device_by_id.get(
                        parent_id
                    )
                )

                if parent:
                    area_id = (
                        parent.get(
                            "area_id"
                        )
                    )

            area_name = (
                area_by_id.get(
                    area_id
                )
                if area_id
                else None
            )

            device_entities = (
                entities_by_device.get(
                    device_id,
                    []
                )
            )

            integrations = sorted(
                {
                    str(
                        entity.get(
                            "platform"
                        )
                    )
                    for entity
                    in device_entities
                    if entity.get(
                        "platform"
                    )
                }
            )

            domains = sorted(
                {
                    str(
                        entity.get(
                            "entity_id",
                            "",
                        )
                    ).split(
                        ".",
                        1,
                    )[0]
                    for entity
                    in device_entities
                    if "." in str(
                        entity.get(
                            "entity_id",
                            ""
                        )
                    )
                }
            )

            entity_output = []

            live_entities = 0
            unavailable = 0

            for entity in (
                device_entities
            ):
                entity_id = (
                    entity.get(
                        "entity_id"
                    )
                )

                state = (
                    states_by_id.get(
                        entity_id
                    )
                )

                if state is not None:
                    live_entities += 1

                state_value = (
                    state.get("state")
                    if state
                    else None
                )

                available = (
                    state is not None
                    and state_value
                    not in {
                        "unavailable",
                        "unknown",
                    }
                )

                if (
                    state is not None
                    and not available
                ):
                    unavailable += 1

                entity_output.append(
                    {
                        "entity_id":
                            entity_id,
                        "name":
                            entity.get(
                                "name"
                            ),
                        "original_name":
                            entity.get(
                                "original_name"
                            ),
                        "platform":
                            entity.get(
                                "platform"
                            ),
                        "domain":
                            (
                                entity_id.split(
                                    ".",
                                    1,
                                )[0]
                                if (
                                    entity_id
                                    and "."
                                    in entity_id
                                )
                                else None
                            ),
                        "available":
                            available,
                        "disabled":
                            bool(
                                entity.get(
                                    "disabled_by"
                                )
                            ),
                    }
                )

            status = self._status(
                live_entities,
                unavailable,
            )

            connections = (
                self._pairs(
                    device.get(
                        "connections"
                    )
                )
            )

            identifiers = (
                self._pairs(
                    device.get(
                        "identifiers"
                    )
                )
            )

            mac = self._mac(
                connections
            )

            ieee = self._ieee(
                identifiers
            )

            ip = self._ip_for(
                name=name,
                device=device,
                device_entities=
                    device_entities,
                states_by_id=
                    states_by_id,
            )

            system = (
                self._is_system(
                    integrations
                )
            )

            category = (
                self._category(
                    integrations,
                    domains,
                    system,
                )
            )

            protocol = (
                self._protocol(
                    integrations,
                    category,
                )
            )

            output.append(
                {
                    "id":
                        device_id,
                    "name":
                        name,
                    "area_id":
                        area_id,
                    "area":
                        area_name,
                    "manufacturer":
                        device.get(
                            "manufacturer"
                        ),
                    "model":
                        device.get(
                            "model"
                        ),
                    "model_id":
                        device.get(
                            "model_id"
                        ),
                    "serial_number":
                        device.get(
                            "serial_number"
                        ),
                    "sw_version":
                        device.get(
                            "sw_version"
                        ),
                    "hw_version":
                        device.get(
                            "hw_version"
                        ),
                    "configuration_url":
                        device.get(
                            "configuration_url"
                        ),
                    "parent_device_id":
                        parent_id,
                    "via_device_id":
                        device.get(
                            "via_device_id"
                        ),
                    "connections":
                        connections,
                    "identifiers":
                        identifiers,
                    "mac":
                        mac,
                    "ieee":
                        ieee,
                    "ip":
                        ip,
                    "integrations":
                        integrations,
                    "domains":
                        domains,
                    "category":
                        category,
                    "protocol":
                        protocol,
                    "system":
                        system,
                    "status":
                        status,
                    "entity_count":
                        len(
                            device_entities
                        ),
                    "live_entity_count":
                        live_entities,
                    "unavailable_count":
                        unavailable,
                    "entities":
                        entity_output,
                }
            )

        output.sort(
            key=lambda item: (
                bool(
                    item["system"]
                ),
                item["area"]
                    or "zzzz",
                item["name"].lower(),
            )
        )

        by_area = Counter(
            item["area"]
            or "Unassigned"
            for item in output
            if not item["system"]
        )

        by_integration = Counter()

        for item in output:
            for integration in (
                item["integrations"]
            ):
                by_integration[
                    integration
                ] += 1

        by_category = Counter(
            item["category"]
            for item in output
        )

        by_protocol = Counter(
            item["protocol"]
            for item in output
        )

        by_status = Counter(
            item["status"]
            for item in output
        )

        physical_devices = [
            item
            for item in output
            if not item["system"]
        ]

        system_devices = [
            item
            for item in output
            if item["system"]
        ]

        return {
            "status":
                "SUCCESS",
            "generated_at":
                generated_at,
            "instance": {
                "url":
                    instance_url,
                "host":
                    (
                        urlparse(
                            instance_url
                        ).hostname
                    ),
            },
            "summary": {
                "devices":
                    len(output),
                "physical_devices":
                    len(
                        physical_devices
                    ),
                "system_devices":
                    len(
                        system_devices
                    ),
                "entities":
                    len(entities),
                "live_states":
                    len(states),
                "areas":
                    len(areas),
                "with_area":
                    sum(
                        bool(
                            item["area"]
                        )
                        for item
                        in physical_devices
                    ),
                "zigbee_devices":
                    by_protocol.get(
                        "Zigbee",
                        0,
                    ),
                "camera_devices":
                    by_category.get(
                        "Camera",
                        0,
                    ),
                "degraded_devices":
                    by_status.get(
                        "DEGRADED",
                        0,
                    ),
                "offline_devices":
                    by_status.get(
                        "OFFLINE",
                        0,
                    ),
                "by_area":
                    dict(
                        sorted(
                            by_area.items()
                        )
                    ),
                "by_integration":
                    dict(
                        sorted(
                            by_integration.items()
                        )
                    ),
                "by_category":
                    dict(
                        sorted(
                            by_category.items()
                        )
                    ),
                "by_protocol":
                    dict(
                        sorted(
                            by_protocol.items()
                        )
                    ),
                "by_status":
                    dict(
                        sorted(
                            by_status.items()
                        )
                    ),
            },
            "areas": [
                {
                    "id":
                        area.get(
                            "area_id"
                        )
                        or area.get(
                            "id"
                        ),
                    "name":
                        area.get(
                            "name"
                        ),
                }
                for area in areas
            ],
            "devices":
                output,
            "error":
                None,
        }


    @staticmethod
    def _clean_name(value):
        """
        Normalize display identity without changing its
        semantic content.

        Removes invisible Unicode format characters,
        normalizes compatibility whitespace and collapses
        accidental repeated whitespace.
        """

        text = html.unescape(
            str(value or "")
        )

        text = unicodedata.normalize(
            "NFKC",
            text,
        )

        text = "".join(
            character
            for character in text
            if unicodedata.category(
                character
            ) != "Cf"
        )

        return " ".join(
            text.split()
        ).strip()

    @staticmethod
    def _websocket_url(
        url,
    ):
        parsed = urlparse(
            url
        )

        scheme = (
            "wss"
            if parsed.scheme
            == "https"
            else "ws"
        )

        return (
            f"{scheme}://"
            f"{parsed.netloc}"
            f"/api/websocket"
        )

    @staticmethod
    def _pairs(value):
        result = []

        for item in (
            value or []
        ):
            if (
                isinstance(
                    item,
                    (list, tuple),
                )
                and len(item) >= 2
            ):
                result.append(
                    [
                        str(item[0]),
                        str(item[1]),
                    ]
                )

        return result

    @staticmethod
    def _mac(connections):
        for kind, value in (
            connections
        ):
            if (
                kind.lower()
                == "mac"
            ):
                return value.lower()

        return None

    @staticmethod
    def _ieee(identifiers):
        for kind, value in (
            identifiers
        ):
            if (
                kind.lower()
                == "zha"
            ):
                return value

        return None

    def _ip_for(
        self,
        *,
        name,
        device,
        device_entities,
        states_by_id,
    ):
        candidates = [
            name,
            device.get(
                "configuration_url"
            ),
        ]

        for entity in (
            device_entities
        ):
            state = (
                states_by_id.get(
                    entity.get(
                        "entity_id"
                    )
                )
            )

            if not state:
                continue

            attributes = (
                state.get(
                    "attributes"
                )
                or {}
            )

            for key in (
                "ip_address",
                "ip",
                "local_ip",
                "host",
                "address",
            ):
                candidates.append(
                    attributes.get(key)
                )

        for candidate in (
            candidates
        ):
            ip = (
                self._extract_ipv4(
                    candidate
                )
            )

            if ip:
                return ip

        return None

    @staticmethod
    def _extract_ipv4(
        value,
    ):
        if value is None:
            return None

        text = str(value)

        patterns = [
            r"(?<!\d)"
            r"(?:\d{1,3}\.){3}"
            r"\d{1,3}"
            r"(?!\d)",

            r"(?<!\d)"
            r"(?:\d{1,3}_){3}"
            r"\d{1,3}"
            r"(?!\d)",
        ]

        for pattern in patterns:
            for match in re.findall(
                pattern,
                text,
            ):
                candidate = (
                    match.replace(
                        "_",
                        ".",
                    )
                )

                try:
                    address = (
                        ipaddress.ip_address(
                            candidate
                        )
                    )
                except ValueError:
                    continue

                if address.version == 4:
                    return str(
                        address
                    )

        return None

    @classmethod
    def _is_system(
        cls,
        integrations,
    ):
        if not integrations:
            return False

        return all(
            integration
            in cls.SYSTEM_INTEGRATIONS
            for integration
            in integrations
        )

    @staticmethod
    def _category(
        integrations,
        domains,
        system,
    ):
        integrations = set(
            integrations
        )

        domains = set(
            domains
        )

        if system:
            return "System"

        if "ezviz" in integrations:
            return "Camera"

        if (
            "camera" in domains
            and "ezviz"
            in integrations
        ):
            return "Camera"

        if "zha" in integrations:
            return "Zigbee"

        if (
            "mobile_app"
            in integrations
        ):
            return "Mobile"

        if (
            "cast"
            in integrations
            or "samsungtv"
            in integrations
        ):
            return "Media"

        if (
            "sonoff"
            in integrations
        ):
            return "IoT"

        if (
            "generic"
            in integrations
        ):
            return "Network"

        return "Device"

    @staticmethod
    def _protocol(
        integrations,
        category,
    ):
        integrations = set(
            integrations
        )

        if "zha" in integrations:
            return "Zigbee"

        if "ezviz" in integrations:
            return "IP / EZVIZ"

        if "sonoff" in integrations:
            return "IP / SONOFF"

        if "mobile_app" in integrations:
            return "Mobile"

        if (
            "cast"
            in integrations
            or "samsungtv"
            in integrations
            or "generic"
            in integrations
        ):
            return "IP / LAN"

        if category == "System":
            return "Home Assistant"

        return (
            sorted(
                integrations
            )[0]
            if integrations
            else "Unknown"
        )

    @staticmethod
    def _status(
        live_entities,
        unavailable,
    ):
        if live_entities <= 0:
            return "UNKNOWN"

        if unavailable >= live_entities:
            return "OFFLINE"

        if unavailable > 0:
            return "DEGRADED"

        return "ONLINE"
