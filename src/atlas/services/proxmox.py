import re
import requests

from atlas.models.proxmox import (
    ProxmoxInfo,
    ProxmoxGuest,
    ProxmoxGuestRuntime,
    ProxmoxNode,
)

from atlas.config.proxmox import (
    require_proxmox_api,
)


class ProxmoxService:

    def __init__(self):

        config = require_proxmox_api()

        self.url = config.url.rstrip("/")

        self.headers = {
            "Authorization":
                config.token,
        }

        self.verify = config.requests_verify


    def _get(
        self,
        endpoint,
    ):

        response = requests.get(
            self.url + endpoint,
            headers=self.headers,
            verify=self.verify,
            timeout=5,
        )

        response.raise_for_status()

        return response.json()["data"]

    def _post(
        self,
        endpoint,
        data=None,
    ):
        """
        Internal authenticated Proxmox POST transport.

        Authorization and safety policy belong to higher layers.
        """

        response = requests.post(
            self.url + endpoint,
            headers=self.headers,
            verify=self.verify,
            timeout=10,
            data=data or {},
        )

        response.raise_for_status()

        return response.json()[
            "data"
        ]


    @staticmethod
    def _hostpci_devices_from_config(
        config: dict,
    ) -> set[str]:
        """
        Extract canonical PCI addresses from QEMU hostpci entries.
        """

        pattern = re.compile(
            r"(?:(?:[0-9a-fA-F]{4}):)?"
            r"[0-9a-fA-F]{2}:"
            r"[0-9a-fA-F]{2}\."
            r"[0-7]"
        )

        devices = set()

        for key, value in config.items():

            if not str(
                key
            ).startswith(
                "hostpci"
            ):
                continue

            if not isinstance(
                value,
                str,
            ):
                continue

            for match in pattern.findall(
                value
            ):

                device = match.lower()

                if device.count(
                    ":"
                ) == 1:

                    device = (
                        "0000:"
                        + device
                    )

                devices.add(
                    device
                )

        return devices


    def qemu_pci_devices(
        self,
        vmid: int,
    ) -> list[str]:
        """
        Return passthrough PCI devices configured for one QEMU VM.
        Read-only.
        """

        guest = self.resolve_guest(
            vmid,
            expected_type="qemu",
        )

        config = self._get(
            f"/api2/json/nodes/"
            f"{guest.node}/qemu/"
            f"{guest.vmid}/config"
        )

        return sorted(
            self._hostpci_devices_from_config(
                config
            )
        )


    def running_qemu_pci_conflicts(
        self,
        vmid: int,
    ) -> list[dict]:
        """
        Detect running QEMU guests sharing passthrough PCI devices
        with the requested VM.

        Read-only. No guest VMIDs are hardcoded.
        """

        target = self.resolve_guest(
            vmid,
            expected_type="qemu",
        )

        target_config = self._get(
            f"/api2/json/nodes/"
            f"{target.node}/qemu/"
            f"{target.vmid}/config"
        )

        target_devices = (
            self._hostpci_devices_from_config(
                target_config
            )
        )

        if not target_devices:
            return []

        resources = self._get(
            "/api2/json/cluster/resources?type=vm"
        )

        conflicts = []

        for item in resources:

            if str(
                item.get(
                    "type",
                    "",
                )
            ).lower() != "qemu":
                continue

            if str(
                item.get(
                    "status",
                    "",
                )
            ).lower() != "running":
                continue

            try:
                other_vmid = int(
                    item.get(
                        "vmid"
                    )
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

            if other_vmid == target.vmid:
                continue

            node = str(
                item.get(
                    "node"
                )
                or ""
            ).strip()

            if not node:
                continue

            config = self._get(
                f"/api2/json/nodes/"
                f"{node}/qemu/"
                f"{other_vmid}/config"
            )

            other_devices = (
                self._hostpci_devices_from_config(
                    config
                )
            )

            shared = sorted(
                target_devices
                & other_devices
            )

            if not shared:
                continue

            conflicts.append(
                {
                    "vmid":
                        other_vmid,

                    "name":
                        str(
                            item.get(
                                "name"
                            )
                            or (
                                f"guest-"
                                f"{other_vmid}"
                            )
                        ),

                    "node":
                        node,

                    "devices":
                        shared,
                }
            )

        return sorted(
            conflicts,
            key=lambda item: item[
                "vmid"
            ],
        )


    def _get_guest_storage(
        self,
        node: str,
        vmid: int,
    ) -> list[dict]:
        """
        Read QEMU guest configuration and expose physical
        storage identities backed by /dev/disk/by-id.
        """

        try:
            config = self._get(
                f"/api2/json/nodes/{node}/qemu/{vmid}/config"
            )
        except Exception:
            return []

        devices = []

        for key, value in config.items():

            if not isinstance(value, str):
                continue

            if not key.startswith(
                ("scsi", "sata", "virtio", "ide")
            ):
                continue

            parts = [
                part.strip()
                for part in value.split(",")
            ]

            if not parts:
                continue

            device = parts[0]

            if not device.startswith(
                "/dev/disk/by-id/"
            ):
                continue

            attributes = {}

            for part in parts[1:]:
                if "=" in part:
                    name, attr_value = part.split(
                        "=",
                        1,
                    )
                    attributes[name] = attr_value

            devices.append(
                {
                    "bus": key,
                    "device": device,
                    "size": attributes.get("size"),
                    "physical": True,
                }
            )

        return devices

    def resolve_guest(
        self,
        vmid: int,
        expected_type: str | None = None,
    ) -> ProxmoxGuestRuntime:
        """
        Resolve one Proxmox guest deterministically by VMID.

        Read-only. Verifies guest type, node and runtime state
        directly against the Proxmox API.
        """

        try:
            guest_vmid = int(
                vmid
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                "invalid Proxmox VMID"
            ) from exc

        if guest_vmid <= 0:
            raise ValueError(
                "invalid Proxmox VMID"
            )

        if expected_type not in (
            None,
            "qemu",
            "lxc",
        ):
            raise ValueError(
                "expected_type must be qemu or lxc"
            )

        resources = self._get(
            "/api2/json/cluster/resources?type=vm"
        )

        matches = []

        for item in resources:

            resource_type = str(
                item.get(
                    "type",
                    "",
                )
            ).lower()

            if resource_type not in (
                "qemu",
                "lxc",
            ):
                continue

            try:
                item_vmid = int(
                    item.get(
                        "vmid"
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if item_vmid != guest_vmid:
                continue

            matches.append(
                item
            )

        if not matches:
            raise LookupError(
                f"Proxmox guest VMID "
                f"{guest_vmid} not found"
            )

        if len(matches) != 1:
            raise RuntimeError(
                f"ambiguous Proxmox VMID "
                f"{guest_vmid}"
            )

        item = matches[0]

        resource_type = str(
            item.get(
                "type",
                "",
            )
        ).lower()

        if (
            expected_type is not None
            and resource_type != expected_type
        ):
            raise ValueError(
                f"Proxmox VMID {guest_vmid} "
                f"is {resource_type}, "
                f"not {expected_type}"
            )

        node = str(
            item.get(
                "node"
            )
            or ""
        ).strip()

        if not node:
            raise RuntimeError(
                f"Proxmox VMID {guest_vmid} "
                f"has no node"
            )

        name = str(
            item.get(
                "name"
            )
            or f"guest-{guest_vmid}"
        )

        status = str(
            item.get(
                "status"
            )
            or "unknown"
        ).lower()

        return ProxmoxGuestRuntime(
            vmid=guest_vmid,
            name=name,
            type=resource_type,
            node=node,
            status=status,
        )


    def get_info(
        self,
    ):

        version = self._get(
            "/api2/json/version"
        )

        resources = self._get(
            "/api2/json/cluster/resources"
        )

        node = "unknown"
        node_info = None
        guests = []

        # Resolve the Proxmox node before processing guests.
        # cluster/resources does not guarantee node entries come first.
        for item in resources:

            if item.get("type") == "node":
                node = item.get(
                    "node",
                    "unknown",
                )
                break

        for item in resources:

            resource_type = item.get("type")

            # ----------------------------------------------------------
            # PROXMOX NODE
            # ----------------------------------------------------------

            if resource_type == "node":

                node = item.get(
                    "node",
                    "unknown",
                )

                node_info = ProxmoxNode(
                    node=node,

                    status=item.get(
                        "status",
                        "unknown",
                    ),

                    memory=item.get(
                        "mem",
                        0,
                    ),

                    max_memory=item.get(
                        "maxmem",
                        0,
                    ),

                    cpu=float(
                        item.get(
                            "cpu",
                            0,
                        )
                    ),

                    max_cpu=int(
                        item.get(
                            "maxcpu",
                            0,
                        )
                    ),

                    disk=item.get(
                        "disk",
                        0,
                    ),

                    max_disk=item.get(
                        "maxdisk",
                        0,
                    ),

                    uptime=int(
                        item.get(
                            "uptime",
                            0,
                        )
                    ),
                )

                continue

            # ----------------------------------------------------------
            # GUESTS
            # ----------------------------------------------------------

            if resource_type not in (
                "qemu",
                "lxc",
            ):
                continue

            vmid = int(
                item.get(
                    "vmid",
                    0,
                )
            )

            guest_storage = []

            if resource_type == "qemu":
                guest_storage = self._get_guest_storage(
                    node,
                    vmid,
                )

            guests.append(
                ProxmoxGuest(
                    vmid=int(
                        item.get(
                            "vmid",
                            0,
                        )
                    ),

                    name=item.get(
                        "name",
                        f"guest-{item.get('vmid')}",
                    ),

                    type=resource_type,

                    status=item.get(
                        "status",
                        "unknown",
                    ),

                    memory=item.get(
                        "mem",
                        0,
                    ),

                    max_memory=item.get(
                        "maxmem",
                        0,
                    ),

                    cpu=float(
                        item.get(
                            "cpu",
                            0,
                        )
                    ),

                    max_cpu=int(
                        item.get(
                            "maxcpu",
                            0,
                        )
                    ),

                    disk=item.get(
                        "disk",
                        0,
                    ),

                    max_disk=item.get(
                        "maxdisk",
                        0,
                    ),

                    disk_read=item.get(
                        "diskread",
                        0,
                    ),

                    disk_write=item.get(
                        "diskwrite",
                        0,
                    ),

                    net_in=item.get(
                        "netin",
                        0,
                    ),

                    net_out=item.get(
                        "netout",
                        0,
                    ),

                    uptime=int(
                        item.get(
                            "uptime",
                            0,
                        )
                    ),

                    storage_devices=guest_storage,
                )
            )

        return ProxmoxInfo(
            version=version["version"],
            release=version["release"],
            node=node,
            node_info=node_info,
            guests=guests,
        )
