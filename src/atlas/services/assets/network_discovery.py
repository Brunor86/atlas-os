from __future__ import annotations

import ipaddress
import json
import os
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from urllib.parse import urlparse


class LocalNetworkDiscoveryService:
    """
    Read-only observer for the directly attached IPv4 LAN.

    The service:
    - discovers the active interface and default gateway;
    - optionally probes only the directly connected private subnet;
    - reads the kernel neighbor table;
    - never modifies network configuration;
    - never scans outside the local subnet.
    """

    MAX_HOSTS = 512
    WORKERS = 64

    def snapshot(
        self,
        *,
        active_scan: bool = True,
    ) -> dict:

        generated_at = datetime.now(
            UTC
        ).isoformat()

        try:
            context = (
                self._network_context()
            )
        except Exception as exc:
            return {
                "status": "ERROR",
                "generated_at":
                    generated_at,
                "error":
                    str(exc),
                "gateway": None,
                "local": None,
                "summary": {
                    "observed_devices": 0,
                    "named_devices": 0,
                    "unknown_devices": 0,
                },
                "devices": [],
            }

        network = ipaddress.ip_network(
            context["cidr"],
            strict=False,
        )

        can_scan = (
            active_scan
            and network.is_private
            and network.num_addresses
            <= self.MAX_HOSTS
        )

        if can_scan:
            self._probe_network(
                network,
                context["local_ip"],
            )

        rows = self._neighbor_rows(
            context["interface"]
        )

        known_names = (
            self._known_names(
                context
            )
        )

        devices = []

        for row in rows:

            ip_text = row.get("dst")

            try:
                address = (
                    ipaddress.ip_address(
                        ip_text
                    )
                )
            except ValueError:
                continue

            if (
                address.version != 4
                or address not in network
            ):
                continue

            state = self._state_text(
                row.get("state")
            )

            if state in {
                "FAILED",
                "INCOMPLETE",
            }:
                continue

            mac = (
                row.get("lladdr")
                or None
            )

            name = (
                known_names.get(
                    ip_text
                )
                or self._reverse_name(
                    ip_text
                )
            )

            kind = (
                self._kind_for(
                    ip_text,
                    name,
                    context,
                )
            )

            if not name:
                name = (
                    f"LAN device "
                    f"{ip_text}"
                )

            devices.append(
                {
                    "ip": ip_text,
                    "mac": mac,
                    "name": name,
                    "kind": kind,
                    "state": state,
                    "status": "ONLINE",
                    "interface":
                        context[
                            "interface"
                        ],
                    "source":
                        "kernel_neighbor_table",
                }
            )

        # The observer itself is not normally present
        # in its own neighbor table. Add it explicitly.
        if not any(
            item["ip"]
            == context["local_ip"]
            for item in devices
        ):
            devices.append(
                {
                    "ip":
                        context[
                            "local_ip"
                        ],
                    "mac":
                        context.get(
                            "local_mac"
                        ),
                    "name":
                        socket.gethostname(),
                    "kind":
                        "atlas_observer",
                    "state":
                        "LOCAL",
                    "status":
                        "ONLINE",
                    "interface":
                        context[
                            "interface"
                        ],
                    "source":
                        "local_interface",
                }
            )

        devices.sort(
            key=lambda item:
                ipaddress.ip_address(
                    item["ip"]
                )
        )

        gateway = next(
            (
                item
                for item in devices
                if item["ip"]
                == context["gateway"]
            ),
            None,
        )

        if gateway is None:
            gateway = {
                "ip":
                    context["gateway"],
                "mac":
                    None,
                "name":
                    "Starlink router",
                "kind":
                    "gateway",
                "state":
                    "UNKNOWN",
                "status":
                    "UNKNOWN",
                "interface":
                    context[
                        "interface"
                    ],
                "source":
                    "default_route",
            }

        else:
            gateway = {
                **gateway,
                "name":
                    "Starlink router",
                "kind":
                    "gateway",
            }

        client_devices = [
            item
            for item in devices
            if item["ip"]
            != context["gateway"]
        ]

        named = sum(
            not item["name"].startswith(
                "LAN device "
            )
            for item
            in client_devices
        )

        return {
            "status": "SUCCESS",
            "generated_at":
                generated_at,
            "mode":
                (
                    "ACTIVE_LOCAL_SCAN"
                    if can_scan
                    else "PASSIVE_NEIGHBOR_CACHE"
                ),
            "gateway":
                gateway,
            "local": {
                "ip":
                    context[
                        "local_ip"
                    ],
                "mac":
                    context.get(
                        "local_mac"
                    ),
                "hostname":
                    socket.gethostname(),
                "interface":
                    context[
                        "interface"
                    ],
                "cidr":
                    context["cidr"],
            },
            "summary": {
                "observed_devices":
                    len(
                        client_devices
                    ),
                "named_devices":
                    named,
                "unknown_devices":
                    (
                        len(
                            client_devices
                        )
                        - named
                    ),
            },
            "devices":
                client_devices,
            "error": None,
        }

    def _network_context(
        self,
    ) -> dict:

        routes = self._json_command(
            [
                "ip",
                "-j",
                "route",
                "show",
                "default",
            ]
        )

        if not routes:
            raise RuntimeError(
                "default route unavailable"
            )

        route = routes[0]

        interface = (
            route.get("dev")
        )

        gateway = (
            route.get("gateway")
        )

        if not interface:
            raise RuntimeError(
                "default interface unavailable"
            )

        if not gateway:
            raise RuntimeError(
                "default gateway unavailable"
            )

        addresses = self._json_command(
            [
                "ip",
                "-j",
                "-4",
                "address",
                "show",
                "dev",
                interface,
            ]
        )

        if not addresses:
            raise RuntimeError(
                "interface address unavailable"
            )

        interface_data = (
            addresses[0]
        )

        inet = next(
            (
                item
                for item
                in interface_data.get(
                    "addr_info",
                    [],
                )
                if (
                    item.get(
                        "family"
                    )
                    == "inet"
                    and item.get(
                        "scope"
                    )
                    == "global"
                )
            ),
            None,
        )

        if inet is None:
            raise RuntimeError(
                "global IPv4 address unavailable"
            )

        local_ip = (
            inet["local"]
        )

        prefixlen = int(
            inet["prefixlen"]
        )

        return {
            "interface":
                interface,
            "gateway":
                gateway,
            "local_ip":
                local_ip,
            "local_mac":
                interface_data.get(
                    "address"
                ),
            "cidr":
                f"{local_ip}/{prefixlen}",
        }

    def _probe_network(
        self,
        network,
        local_ip,
    ):

        hosts = [
            str(address)
            for address
            in network.hosts()
            if str(address)
            != local_ip
        ]

        def probe(address):
            try:
                subprocess.run(
                    [
                        "ping",
                        "-n",
                        "-c",
                        "1",
                        "-W",
                        "1",
                        address,
                    ],
                    stdout=
                        subprocess.DEVNULL,
                    stderr=
                        subprocess.DEVNULL,
                    timeout=1.4,
                    check=False,
                )
            except (
                OSError,
                subprocess.TimeoutExpired,
            ):
                return

        with ThreadPoolExecutor(
            max_workers=self.WORKERS
        ) as executor:
            list(
                executor.map(
                    probe,
                    hosts,
                )
            )

    def _neighbor_rows(
        self,
        interface,
    ):
        return self._json_command(
            [
                "ip",
                "-j",
                "neigh",
                "show",
                "dev",
                interface,
            ]
        )

    def _known_names(
        self,
        context,
    ) -> dict:

        names = {
            context["gateway"]:
                "Starlink router",

            context["local_ip"]:
                socket.gethostname(),
        }

        proxmox_url = os.getenv(
            "ATLAS_PROXMOX_URL",
            "",
        )

        if proxmox_url:
            host = urlparse(
                proxmox_url
            ).hostname

            if host:
                try:
                    ipaddress.ip_address(
                        host
                    )
                except ValueError:
                    pass
                else:
                    names[host] = (
                        "atlas · Proxmox"
                    )

        proxmox_host = os.getenv(
            "ATLAS_PROXMOX_HOST",
            "",
        )

        if "@" in proxmox_host:
            proxmox_host = (
                proxmox_host
                .rsplit(
                    "@",
                    1,
                )[1]
            )

        if proxmox_host:
            try:
                ipaddress.ip_address(
                    proxmox_host
                )
            except ValueError:
                pass
            else:
                names[
                    proxmox_host
                ] = "atlas · Proxmox"

        ollama_host = os.getenv(
            "ATLAS_OLLAMA_HOST",
            "",
        )

        if ollama_host:
            try:
                ipaddress.ip_address(
                    ollama_host
                )
            except ValueError:
                pass
            else:
                names[
                    ollama_host
                ] = "atlas-ai"

        for candidate in (
            "homeassistant",
            "homeassistant.local",
        ):
            address = (
                self._resolve_ipv4(
                    candidate
                )
            )

            if address:
                names[
                    address
                ] = "Home Assistant"

        return names

    def _kind_for(
        self,
        ip_text,
        name,
        context,
    ):
        if (
            ip_text
            == context[
                "gateway"
            ]
        ):
            return "gateway"

        if (
            ip_text
            == context[
                "local_ip"
            ]
        ):
            return "atlas_observer"

        value = (
            str(name or "")
            .lower()
        )

        if "proxmox" in value:
            return "proxmox"

        if "home assistant" in value:
            return "home_assistant"

        if "atlas-ai" in value:
            return "atlas_ai"

        return "lan_device"

    def _reverse_name(
        self,
        ip_text,
    ):
        try:
            result = subprocess.run(
                [
                    "getent",
                    "hosts",
                    ip_text,
                ],
                capture_output=True,
                text=True,
                timeout=0.6,
                check=False,
            )
        except (
            OSError,
            subprocess.TimeoutExpired,
        ):
            return None

        if result.returncode:
            return None

        first = (
            result.stdout
            .strip()
            .splitlines()
        )

        if not first:
            return None

        parts = first[0].split()

        if len(parts) < 2:
            return None

        name = (
            parts[1]
            .split(".")[0]
        )

        return name or None

    def _resolve_ipv4(
        self,
        hostname,
    ):
        try:
            result = subprocess.run(
                [
                    "getent",
                    "ahostsv4",
                    hostname,
                ],
                capture_output=True,
                text=True,
                timeout=0.6,
                check=False,
            )
        except (
            OSError,
            subprocess.TimeoutExpired,
        ):
            return None

        if result.returncode:
            return None

        for line in (
            result.stdout
            .splitlines()
        ):
            parts = line.split()

            if not parts:
                continue

            try:
                address = (
                    ipaddress.ip_address(
                        parts[0]
                    )
                )
            except ValueError:
                continue

            if address.version == 4:
                return str(
                    address
                )

        return None

    @staticmethod
    def _state_text(
        value,
    ):
        if isinstance(
            value,
            list,
        ):
            return (
                value[0]
                if value
                else "UNKNOWN"
            )

        return str(
            value
            or "UNKNOWN"
        )

    @staticmethod
    def _json_command(
        command,
    ):
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )

        if result.returncode:
            raise RuntimeError(
                "command failed: "
                + " ".join(
                    command
                )
                + ": "
                + result.stderr.strip()
            )

        return json.loads(
            result.stdout
            or "[]"
        )
