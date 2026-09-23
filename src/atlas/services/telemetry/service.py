from __future__ import annotations

import os
import socket
import subprocess
from pathlib import Path
from typing import Any

import psutil

from atlas.collectors.smart import SmartCollector
from atlas.services.metrics import MetricsService


from atlas.config.proxmox import (
    require_proxmox_host,
)

class TelemetryService:
    """
    ATLAS physical and operational telemetry layer.

    This service is deliberately independent from the LLM.

    It exposes deterministic infrastructure facts such as:

    - CPU usage
    - CPU cores
    - CPU frequency
    - RAM
    - load average
    - temperatures
    - filesystem usage
    - physical disks / SMART
    - network interfaces
    - processes
    - network connections
    - Prometheus metrics
    - filesystem/path sizes

    The AI Operator can consume this service later through tools.
    """

    def __init__(
        self,
        metrics_service: MetricsService | None = None,
    ) -> None:

        self.metrics = (
            metrics_service
            or MetricsService()
        )

    # ------------------------------------------------------------------
    # SYSTEM
    # ------------------------------------------------------------------

    def system(self) -> dict[str, Any]:

        cpu_percent = psutil.cpu_percent(
            interval=0.1
        )

        cpu_times = psutil.cpu_times()

        memory = psutil.virtual_memory()

        swap = psutil.swap_memory()

        try:
            load = os.getloadavg()

        except (AttributeError, OSError):
            load = (
                None,
                None,
                None,
            )

        frequency = psutil.cpu_freq()

        return {
            "hostname": socket.gethostname(),

            "cpu": {
                "percent": cpu_percent,

                "logical_cores":
                    psutil.cpu_count(
                        logical=True
                    ),

                "physical_cores":
                    psutil.cpu_count(
                        logical=False
                    ),

                "frequency_mhz": (
                    round(
                        frequency.current,
                        1,
                    )
                    if frequency
                    else None
                ),

                "frequency_min_mhz": (
                    round(
                        frequency.min,
                        1,
                    )
                    if frequency
                    else None
                ),

                "frequency_max_mhz": (
                    round(
                        frequency.max,
                        1,
                    )
                    if frequency
                    else None
                ),
            },

            "memory": {
                "percent": memory.percent,
                "total_gb": round(
                    memory.total / 1024**3,
                    2,
                ),
                "used_gb": round(
                    memory.used / 1024**3,
                    2,
                ),
                "available_gb": round(
                    memory.available / 1024**3,
                    2,
                ),
            },

            "swap": {
                "percent": swap.percent,
                "total_gb": round(
                    swap.total / 1024**3,
                    2,
                ),
                "used_gb": round(
                    swap.used / 1024**3,
                    2,
                ),
            },

            "load_average": {
                "1m": load[0],
                "5m": load[1],
                "15m": load[2],
            },

            "cpu_times": {
                "user": cpu_times.user,
                "system": cpu_times.system,
                "idle": cpu_times.idle,
            },
        }

    # ------------------------------------------------------------------
    # TEMPERATURES
    # ------------------------------------------------------------------

    def temperatures(self) -> list[dict[str, Any]]:

        result: list[dict[str, Any]] = []

        try:
            sensors = psutil.sensors_temperatures(
                fahrenheit=False
            )
        except Exception:
            sensors = {}

        for sensor_name, entries in sensors.items():

            for entry in entries:

                result.append(
                    {
                        "sensor": sensor_name,
                        "label": entry.label,
                        "temperature_c": entry.current,
                        "high_c": entry.high,
                        "critical_c": entry.critical,
                    }
                )

        return result

    # ------------------------------------------------------------------
    # DISKS / FILESYSTEMS
    # ------------------------------------------------------------------

    def filesystems(self) -> list[dict[str, Any]]:

        result = []

        ignored = {
            "/proc",
            "/sys",
            "/dev",
            "/run",
            "/boot/efi",
        }

        for partition in psutil.disk_partitions(
            all=False
        ):

            mountpoint = partition.mountpoint

            if mountpoint in ignored:
                continue

            try:
                usage = psutil.disk_usage(
                    mountpoint
                )
            except (
                PermissionError,
                FileNotFoundError,
                OSError,
            ):
                continue

            result.append(
                {
                    "device": partition.device,
                    "mountpoint": mountpoint,
                    "filesystem": partition.fstype,
                    "total_gb": round(
                        usage.total / 1024**3,
                        2,
                    ),
                    "used_gb": round(
                        usage.used / 1024**3,
                        2,
                    ),
                    "free_gb": round(
                        usage.free / 1024**3,
                        2,
                    ),
                    "usage_percent": round(
                        usage.percent,
                        2,
                    ),
                }
            )

        return result

    # ------------------------------------------------------------------
    # PHYSICAL BLOCK DEVICES
    # ------------------------------------------------------------------

    def block_devices(self) -> list[dict[str, Any]]:

        command = [
            "lsblk",
            "-J",
            "-b",
            "-dn",
            "-o",
            "NAME,SIZE,MODEL,SERIAL,TYPE,MOUNTPOINT",
        ]

        try:

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

        except (
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):

            return []

        if result.returncode != 0:
            return []

        try:
            import json

            payload = json.loads(
                result.stdout
            )

        except (
            json.JSONDecodeError,
            TypeError,
        ):

            return []

        devices = []

        for item in payload.get("blockdevices", []):

            if item.get("type") != "disk":
                continue

            name = (
                item.get("name")
                or ""
            ).strip()

            if not name:
                continue

            devices.append(
                {
                    "device": f"/dev/{name}",
                    "name": name,
                    "type": "disk",
                    "model": (
                        item.get("model")
                        or ""
                    ).strip(),
                    "serial": (
                        item.get("serial")
                        or ""
                    ).strip(),
                    "size": item.get("size"),
                    "mountpoint": (
                        item.get("mountpoint")
                    ),
                }
            )

        return devices

    # ------------------------------------------------------------------
    # SMART
    # ------------------------------------------------------------------

    def smart(
        self,
        device: str | None = None,
    ) -> list[dict[str, Any]]:

        devices = self.block_devices()

        if device:

            requested = device.strip()

            if not requested.startswith("/dev/"):
                requested = (
                    f"/dev/{requested}"
                )

            devices = [
                item
                for item in devices
                if item["device"] == requested
            ]

        result = []

        for item in devices:

            device = item["device"]
            model = item.get("model", "").strip()

            # ----------------------------------------------------------
            # Physical disks hidden behind Proxmox/QEMU
            # ----------------------------------------------------------
            #
            # Inside the Debian VM the disk appears as QEMU HARDDISK.
            # The physical SMART data is therefore obtained through
            # the Proxmox SMART collector.
            #
            if model.upper() == "QEMU HARDDISK":

                try:

                    from atlas.services.proxmox import (
                        ProxmoxService,
                    )

                    from atlas.collectors.proxmox.smart import (
                        ProxmoxSmartCollector,
                    )

                    physical_device = None

                    # --------------------------------------------------
                    # Resolve the physical Proxmox disk backing this
                    # QEMU guest disk.
                    # --------------------------------------------------

                    proxmox = ProxmoxService()
                    proxmox_info = proxmox.get_info()

                    guest_size = item.get(
                        "size",
                        0,
                    )

                    for guest in proxmox_info.guests:

                        for storage in (
                            guest.storage_devices or []
                        ):

                            if not storage.get(
                                "physical"
                            ):
                                continue

                            size = storage.get(
                                "size",
                                "",
                            )

                            if not size:
                                continue

                            # Proxmox reports physical disk size
                            # as e.g. "11176G". Match against the
                            # guest block-device size with tolerance.
                            if (
                                isinstance(
                                    guest_size,
                                    int,
                                )
                                and size.endswith("G")
                            ):

                                try:
                                    physical_gb = float(
                                        size[:-1]
                                    )

                                    guest_gb = (
                                        guest_size
                                        / (
                                            1024 ** 3
                                        )
                                    )

                                    if abs(
                                        physical_gb
                                        - guest_gb
                                    ) < 100:
                                        physical_device = (
                                            storage.get(
                                                "device"
                                            )
                                        )
                                        break

                                except (
                                    ValueError,
                                    TypeError,
                                ):
                                    pass

                        if physical_device:
                            break

                    if not physical_device:

                        result.append(
                            {
                                "device": device,
                                "model": model,
                                "temperature_c": None,
                                "power_on_hours": None,
                                "health": "",
                                "smart_available": False,
                                "smart_passed": False,
                                "source": "proxmox-smart",
                                "error": (
                                    "physical backing device "
                                    "could not be resolved"
                                ),
                            }
                        )

                        continue

                    infos = ProxmoxSmartCollector(
                        require_proxmox_host(),
                        physical_device,
                    ).collect()

                    for info in infos:

                        result.append(
                            {
                                "device":
                                    device,

                                "physical_device":
                                    info.device,

                                "model":
                                    info.model,

                                "serial":
                                    info.serial,

                                "vendor":
                                    info.vendor,

                                "firmware":
                                    info.firmware,

                                "temperature_c":
                                    info.temperature,

                                "power_on_hours":
                                    info.power_on_hours,

                                "health":
                                    info.health,

                                "smart_available":
                                    info.smart_available,

                                "smart_passed":
                                    info.smart_passed,

                                "source":
                                    "proxmox-smart",
                            }
                        )

                    continue

                except Exception as exc:

                    result.append(
                        {
                            "device":
                                device,

                            "model":
                                model,

                            "status":
                                "ERROR",

                            "error":
                                str(exc),

                            "source":
                                "proxmox-smart",
                        }
                    )

                    continue

            # ----------------------------------------------------------
            # Direct SMART
            # ----------------------------------------------------------

            try:

                infos = SmartCollector(
                    device
                ).collect()

            except Exception as exc:

                result.append(
                    {
                        "device":
                            device,

                        "model":
                            model,

                        "status":
                            "ERROR",

                        "error":
                            str(exc),
                    }
                )

                continue

            for info in infos:

                result.append(
                    {
                        "device":
                            info.device,

                        "model":
                            info.model,

                        "serial":
                            info.serial,

                        "vendor":
                            info.vendor,

                        "firmware":
                            info.firmware,

                        "temperature_c":
                            info.temperature,

                        "power_on_hours":
                            info.power_on_hours,

                        "health":
                            info.health,

                        "smart_available":
                            info.smart_available,

                        "smart_passed":
                            info.smart_passed,

                        "source":
                            "smart",
                    }
                )

        return result

    # ------------------------------------------------------------------
    # NETWORK INTERFACES
    # ------------------------------------------------------------------

    def network_interfaces(
        self,
    ) -> list[dict[str, Any]]:

        addresses = psutil.net_if_addrs()
        statistics = psutil.net_if_stats()
        counters = psutil.net_io_counters(
            pernic=True
        )

        result = []

        for interface, addr_list in addresses.items():

            stats = statistics.get(
                interface
            )

            io = counters.get(
                interface
            )

            ips = []

            mac = None

            for address in addr_list:

                if address.family == socket.AF_INET:

                    ips.append(
                        address.address
                    )

                elif str(
                    address.family
                ) in (
                    "AddressFamily.AF_PACKET",
                    "AddressFamily.AF_LINK",
                ):

                    mac = address.address

            result.append(
                {
                    "interface": interface,

                    "up": (
                        stats.isup
                        if stats
                        else False
                    ),

                    "speed_mbps": (
                        stats.speed
                        if stats
                        else None
                    ),

                    "mtu": (
                        stats.mtu
                        if stats
                        else None
                    ),

                    "ipv4": ips,

                    "mac": mac,

                    "rx_mb": (
                        round(
                            io.bytes_recv
                            / 1024**2,
                            2,
                        )
                        if io
                        else None
                    ),

                    "tx_mb": (
                        round(
                            io.bytes_sent
                            / 1024**2,
                            2,
                        )
                        if io
                        else None
                    ),
                }
            )

        return result

    # ------------------------------------------------------------------
    # PROCESSES
    # ------------------------------------------------------------------

    def processes(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:

        processes = []

        for process in psutil.process_iter(
            [
                "pid",
                "name",
                "username",
                "cpu_percent",
                "memory_percent",
                "cmdline",
            ]
        ):

            try:

                info = process.info

                processes.append(
                    {
                        "pid":
                            info["pid"],

                        "name":
                            info["name"],

                        "username":
                            info["username"],

                        "cpu_percent":
                            info["cpu_percent"],

                        "memory_percent":
                            round(
                                info[
                                    "memory_percent"
                                ]
                                or 0,
                                2,
                            ),

                        "cmdline":
                            " ".join(
                                info[
                                    "cmdline"
                                ]
                                or []
                            ),
                    }
                )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
            ):
                continue

        processes.sort(
            key=lambda item:
                item["cpu_percent"] or 0,
            reverse=True,
        )

        return processes[:limit]

    # ------------------------------------------------------------------
    # NETWORK CONNECTIONS
    # ------------------------------------------------------------------

    def network_connections(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:

        result = []

        try:

            connections = (
                psutil.net_connections(
                    kind="inet"
                )
            )

        except (
            psutil.AccessDenied,
            PermissionError,
        ):

            return []

        for connection in connections[:limit]:

            process_name = None

            if connection.pid:

                try:

                    process_name = (
                        psutil.Process(
                            connection.pid
                        ).name()
                    )

                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                ):
                    pass

            result.append(
                {
                    "pid":
                        connection.pid,

                    "process":
                        process_name,

                    "family":
                        str(
                            connection.family
                        ),

                    "type":
                        str(
                            connection.type
                        ),

                    "local":
                        (
                            f"{connection.laddr.ip}:"
                            f"{connection.laddr.port}"
                            if connection.laddr
                            else None
                        ),

                    "remote":
                        (
                            f"{connection.raddr.ip}:"
                            f"{connection.raddr.port}"
                            if connection.raddr
                            else None
                        ),

                    "status":
                        connection.status,
                }
            )

        return result

    # ------------------------------------------------------------------
    # PATH / APPLICATION SIZE
    # ------------------------------------------------------------------

    def path_size(self, path: str) -> dict:
        """
        Return filesystem object size.

        The raw byte count is always preserved. Human-readable values
        intentionally keep sub-MB values above zero so small files are
        not reported as 0.0 MB.
        """

        target = Path(path)

        if not target.exists():
            return {
                "path": str(target),
                "exists": False,
                "bytes": 0,
                "mb": 0.0,
                "gb": 0.0,
            }

        if target.is_file():
            size = target.stat().st_size

        elif target.is_dir():
            size = sum(
                entry.stat().st_size
                for entry in target.rglob("*")
                if entry.is_file()
            )

        else:
            size = 0

        mb = size / (1024 ** 2)
        gb = size / (1024 ** 3)

        return {
            "path": str(target),
            "exists": True,
            "bytes": size,
            "mb": mb,
            "gb": gb,
        }

    def atlas_database_size(
        self,
        database_path: str = "atlas.db",
    ) -> dict[str, Any]:

        return self.path_size(
            database_path
        )

    # ------------------------------------------------------------------
    # PROXMOX HOST TELEMETRY
    # ------------------------------------------------------------------

    def proxmox_cpu_temperature(self) -> dict[str, Any]:

        command = (
            "for hwmon in /sys/class/hwmon/hwmon*; do "
            "name=$(cat \"$hwmon/name\" 2>/dev/null || true); "
            "if [ \"$name\" = \"k10temp\" ]; then "
            "for input in \"$hwmon\"/temp*_input; do "
            "cat \"$input\"; "
            "exit 0; "
            "done; "
            "fi; "
            "done"
        )

        result = subprocess.run(
            [
                "ssh",
                require_proxmox_host(),
                command,
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                result.stderr.strip()
                or "Unable to read Proxmox CPU temperature"
            )

        value = result.stdout.strip()

        if not value:
            raise RuntimeError(
                "k10temp sensor not found on Proxmox host"
            )

        temperature_c = int(value) / 1000

        return {
            "host": require_proxmox_host(),
            "sensor": "k10temp",
            "temperature_c": round(
                temperature_c,
                2,
            ),
        }


    def proxmox_storage(self) -> dict[str, Any]:

        # --------------------------------------------------------------
        # Physical disks
        # --------------------------------------------------------------

        disks = subprocess.run(
            [
                "ssh",
                require_proxmox_host(),
                "lsblk",
                "-b",
                "-d",
                "-o",
                "NAME,SIZE,MODEL,SERIAL",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if disks.returncode != 0:
            raise RuntimeError(
                disks.stderr.strip()
                or "Unable to read Proxmox block devices"
            )

        physical_disks = []

        lines = [
            line.strip()
            for line in disks.stdout.splitlines()[1:]
            if line.strip()
        ]

        for line in lines:

            parts = line.split(
                None,
                3,
            )

            if len(parts) < 2:
                continue

            name = parts[0]
            size = int(parts[1])

            model = (
                parts[2].strip()
                if len(parts) >= 3
                else ""
            )

            serial = (
                parts[3].strip()
                if len(parts) >= 4
                else ""
            )

            physical_disks.append(
                {
                    "device": f"/dev/{name}",
                    "size_bytes": size,
                    "size_gb": round(
                        size / 1024**3,
                        2,
                    ),
                    "model": model,
                    "serial": serial,
                }
            )

        # --------------------------------------------------------------
        # LVM physical volume
        # --------------------------------------------------------------

        pvs = subprocess.run(
            [
                "ssh",
                require_proxmox_host(),
                "/usr/sbin/pvs",
                "--units",
                "g",
                "--nosuffix",
                "--noheadings",
                "-o",
                "pv_name,vg_name,pv_size,pv_free",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if pvs.returncode != 0:
            raise RuntimeError(
                pvs.stderr.strip()
                or "Unable to read Proxmox LVM"
            )

        pv_lines = [
            line.split()
            for line in pvs.stdout.splitlines()
            if line.strip()
        ]

        if not pv_lines:
            raise RuntimeError(
                "No Proxmox LVM physical volume found"
            )

        pv_name, vg_name, pv_size, pv_free = pv_lines[0]

        # --------------------------------------------------------------
        # LVM logical volumes
        # --------------------------------------------------------------

        lvs = subprocess.run(
            [
                "ssh",
                require_proxmox_host(),
                "/usr/sbin/lvs",
                "--units",
                "g",
                "--nosuffix",
                "--noheadings",
                "-o",
                "lv_name,lv_size,data_percent",
                "pve",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if lvs.returncode != 0:
            raise RuntimeError(
                lvs.stderr.strip()
                or "Unable to read Proxmox logical volumes"
            )

        logical_volumes = []
        thin_pool = None

        for line in lvs.stdout.splitlines():

            parts = line.split()

            if len(parts) < 2:
                continue

            name = parts[0]
            size_gb = float(parts[1])

            data_percent = None

            if len(parts) >= 3:
                raw_percent = parts[2].strip()

                if raw_percent not in (
                    "",
                    "-",
                ):
                    try:
                        data_percent = float(
                            raw_percent.replace(
                                "%",
                                "",
                            )
                        )
                    except ValueError:
                        data_percent = None

            logical_volumes.append(
                {
                    "name": name,
                    "size_gb": round(
                        size_gb,
                        2,
                    ),
                    "data_percent": data_percent,
                }
            )

            if name == "data":

                free_gb = None

                if data_percent is not None:
                    free_gb = (
                        size_gb
                        * (
                            1
                            - data_percent / 100
                        )
                    )

                thin_pool = {
                    "name": "pve/data",
                    "size_gb": round(
                        size_gb,
                        2,
                    ),
                    "used_percent": (
                        round(
                            data_percent,
                            2,
                        )
                        if data_percent is not None
                        else None
                    ),
                    "free_gb": (
                        round(
                            free_gb,
                            2,
                        )
                        if free_gb is not None
                        else None
                    ),
                }

        return {
            "host": require_proxmox_host(),
            "physical_disks": physical_disks,
            "lvm": {
                "physical_volume": pv_name,
                "volume_group": vg_name,
                "size_gb": round(
                    float(pv_size),
                    2,
                ),
                "free_gb": round(
                    float(pv_free),
                    2,
                ),
            },
            "logical_volumes": logical_volumes,
            "thin_pool": thin_pool,
        }


    # ------------------------------------------------------------------
    # PROMETHEUS
    # ------------------------------------------------------------------

    def prometheus_query(
        self,
        expression: str,
    ) -> Any:

        if not expression:

            raise ValueError(
                "expression is required"
            )

        return self.metrics.prometheus.query(
            expression
        )

    # ------------------------------------------------------------------
    # FULL SNAPSHOT
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:

        return {
            "system":
                self.system(),

            "temperatures":
                self.temperatures(),

            "filesystems":
                self.filesystems(),

            "block_devices":
                self.block_devices(),

            "smart":
                self.smart(),

            "network_interfaces":
                self.network_interfaces(),

            "network_connections":
                self.network_connections(
                    limit=100
                ),

            "processes":
                self.processes(
                    limit=20
                ),
        }
