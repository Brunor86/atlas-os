from __future__ import annotations

import ipaddress
import re
from copy import deepcopy
from datetime import UTC, datetime

from atlas.services.assets.home_assistant_discovery import (
    HomeAssistantDiscoveryService,
)
from atlas.services.assets.network_discovery import (
    LocalNetworkDiscoveryService,
)
from atlas.services.assets.proxmox_guest_network import (
    ProxmoxGuestNetworkService,
)


class IdentityReconciliationService:
    """
    Merge independent read-only observations into a
    single LAN identity view.

    Confidence order:
      1. exact MAC
      2. exact IP
      3. existing ATLAS/network identity

    No fuzzy matching is used.
    """

    def __init__(
        self,
        network_service=None,
        home_assistant_service=None,
        proxmox_service=None,
    ):
        self.network = (
            network_service
            or LocalNetworkDiscoveryService()
        )

        self.home_assistant = (
            home_assistant_service
            or HomeAssistantDiscoveryService()
        )

        self.proxmox = (
            proxmox_service
            or ProxmoxGuestNetworkService()
        )

    def snapshot(
        self,
        *,
        active_scan=True,
    ):
        generated_at = datetime.now(
            UTC
        ).isoformat()

        network = self.network.snapshot(
            active_scan=active_scan
        )

        home_assistant = (
            self.home_assistant.snapshot()
        )

        proxmox = (
            self.proxmox.snapshot()
        )

        devices = deepcopy(
            network.get(
                "devices",
                [],
            )
        )

        #
        # Preserve the original observation source before
        # adding Proxmox / Home Assistant evidence.
        #
        for item in devices:
            original_source = (
                item.get("source")
            )

            item["sources"] = (
                [original_source]
                if original_source
                else []
            )

        by_mac = {
            self._mac(
                item.get("mac")
            ):
                item
            for item in devices
            if self._mac(
                item.get("mac")
            )
        }

        by_ip = {
            item.get("ip"):
                item
            for item in devices
            if item.get("ip")
        }

        matches = []

        #
        # Proxmox guests first because their identity
        # is authoritative for the virtualization layer.
        #
        for guest in (
            proxmox.get(
                "guests",
                []
            )
        ):
            match = None
            method = None

            mac = self._mac(
                guest.get("mac")
            )

            ip = guest.get("ip")

            if mac:
                match = by_mac.get(
                    mac
                )

                if match:
                    method = "MAC"

            if (
                match is None
                and ip
            ):
                match = by_ip.get(ip)

                if match:
                    method = "IP"

            if (
                match is None
                and ip
                and self._valid_ipv4(
                    ip
                )
                and guest.get(
                    "status"
                ) == "running"
            ):
                match = {
                    "ip": ip,
                    "mac": mac,
                    "name":
                        guest["name"],
                    "kind":
                        "proxmox_guest",
                    "state":
                        "DIRECT",
                    "status":
                        "ONLINE",
                    "interface":
                        None,
                    "source":
                        "proxmox",
                }

                devices.append(match)
                by_ip[ip] = match

                if mac:
                    by_mac[mac] = match

                method = (
                    "PROXMOX_LIVE_IP"
                )

            if match is not None:
                original_name = (
                    match.get("name")
                )

                match.update(
                    {
                        "name":
                            guest["name"],
                        "kind":
                            (
                                "vm"
                                if guest[
                                    "guest_type"
                                ]
                                == "QEMU"
                                else "lxc"
                            ),
                        "proxmox": {
                            "vmid":
                                guest["vmid"],
                            "guest_type":
                                guest[
                                    "guest_type"
                                ],
                            "status":
                                guest[
                                    "status"
                                ],
                        },
                    }
                )

                self._source(
                    match,
                    "proxmox",
                )

                matches.append(
                    {
                        "source":
                            "PROXMOX",
                        "name":
                            guest["name"],
                        "ip":
                            match.get("ip"),
                        "method":
                            method,
                        "previous_name":
                            original_name,
                    }
                )

        #
        # Home Assistant devices are then used to add
        # human friendly identity to LAN clients.
        #
        for ha in (
            home_assistant.get(
                "devices",
                []
            )
        ):
            if ha.get("system"):
                continue

            match = None
            method = None

            mac = self._mac(
                ha.get("mac")
            )

            ip = ha.get("ip")

            if mac:
                match = by_mac.get(mac)

                if match:
                    method = "MAC"

            if (
                match is None
                and ip
            ):
                match = by_ip.get(ip)

                if match:
                    method = "IP"

            if match is None:
                continue

            original_name = (
                match.get("name")
            )

            ha_name = (
                ha.get("name")
                or original_name
            )

            #
            # Do not replace a good infrastructure name
            # with a synthetic generic IP-based HA name.
            #
            synthetic = (
                self._synthetic_ip_name(
                    ha_name
                )
            )

            if (
                not synthetic
                or self._generic_lan_name(
                    original_name
                )
            ):
                match["name"] = ha_name

            match[
                "home_assistant"
            ] = {
                "device_id":
                    ha.get("id"),
                "name":
                    ha_name,
                "area":
                    ha.get("area"),
                "manufacturer":
                    ha.get(
                        "manufacturer"
                    ),
                "model":
                    ha.get("model"),
                "protocol":
                    ha.get("protocol"),
                "category":
                    ha.get("category"),
                "status":
                    ha.get("status"),
                "entity_count":
                    ha.get(
                        "entity_count"
                    ),
            }

            self._source(
                match,
                "home_assistant",
            )

            matches.append(
                {
                    "source":
                        "HOME_ASSISTANT",
                    "name":
                        ha_name,
                    "ip":
                        match.get("ip"),
                    "method":
                        method,
                    "previous_name":
                        original_name,
                }
            )

        for item in devices:
            item.setdefault(
                "sources",
                [
                    item.get(
                        "source",
                        "network"
                    )
                ],
            )

            if item.get(
                "home_assistant"
            ):
                item["identified"] = True

            elif item.get(
                "proxmox"
            ):
                item["identified"] = True

            else:
                item["identified"] = (
                    not self._generic_lan_name(
                        item.get("name")
                    )
                )

        devices.sort(
            key=lambda item:
                ipaddress.ip_address(
                    item["ip"]
                )
                if self._valid_ipv4(
                    item.get("ip")
                )
                else ipaddress.ip_address(
                    "255.255.255.255"
                )
        )

        identified = sum(
            bool(
                item.get(
                    "identified"
                )
            )
            for item in devices
        )

        return {
            "status": "SUCCESS",
            "generated_at":
                generated_at,
            "mode":
                network.get(
                    "mode"
                ),
            "gateway":
                network.get(
                    "gateway"
                ),
            "local":
                network.get(
                    "local"
                ),
            "summary": {
                "observed_devices":
                    len(devices),
                "identified_devices":
                    identified,
                "unknown_devices":
                    (
                        len(devices)
                        - identified
                    ),
                "reconciliations":
                    len(matches),
                "ha_devices":
                    (
                        home_assistant
                        .get(
                            "summary",
                            {}
                        )
                        .get(
                            "devices",
                            0,
                        )
                    ),
                "proxmox_guests":
                    len(
                        proxmox.get(
                            "guests",
                            []
                        )
                    ),
            },
            "devices":
                devices,
            "reconciliations":
                matches,
            "proxmox_guests":
                proxmox.get(
                    "guests",
                    []
                ),
            "components": {
                "network":
                    network.get(
                        "status"
                    ),
                "home_assistant":
                    home_assistant.get(
                        "status"
                    ),
                "proxmox":
                    proxmox.get(
                        "status"
                    ),
            },
            "error": None,
        }

    @staticmethod
    def _source(
        item,
        source,
    ):
        sources = item.setdefault(
            "sources",
            [],
        )

        if source not in sources:
            sources.append(source)

    @staticmethod
    def _mac(value):
        if not value:
            return None

        return str(value).lower()

    @staticmethod
    def _valid_ipv4(value):
        if not value:
            return False

        try:
            address = (
                ipaddress.ip_address(
                    value
                )
            )
        except ValueError:
            return False

        return address.version == 4

    @staticmethod
    def _generic_lan_name(value):
        return bool(
            re.fullmatch(
                r"LAN device \d+\.\d+\.\d+\.\d+",
                str(value or ""),
            )
        )

    @staticmethod
    def _synthetic_ip_name(value):
        return bool(
            re.fullmatch(
                r"\d{1,3}(?:_\d{1,3}){3}",
                str(value or ""),
            )
        )
