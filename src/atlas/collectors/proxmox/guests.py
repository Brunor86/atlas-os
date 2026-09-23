from atlas.services.proxmox import ProxmoxService


class ProxmoxGuestDiscovery:

    def __init__(self, host=None):

        self.proxmox = ProxmoxService()

    def discover(self):

        info = self.proxmox.get_info()

        guests = []

        for guest in info.guests:

            if guest.type == "qemu":

                asset_type = "VM"

            elif guest.type == "lxc":

                asset_type = "LXC"

            else:

                continue

            memory_percent = (

                (
                    guest.memory
                    / guest.max_memory
                ) * 100

                if guest.max_memory

                else 0

            )

            guests.append(
                {
                    "type": asset_type,

                    "vmid": str(
                        guest.vmid
                    ),

                    "hostname": guest.name,

                    "status": guest.status,

                    # -------------------------------------------------
                    # CPU
                    # -------------------------------------------------

                    "cpu": guest.cpu,

                    "max_cpu": guest.max_cpu,

                    # -------------------------------------------------
                    # MEMORY
                    # -------------------------------------------------

                    "memory": guest.memory,

                    "max_memory": (
                        guest.max_memory
                    ),

                    "memory_percent": round(
                        memory_percent,
                        2,
                    ),

                    # -------------------------------------------------
                    # DISK
                    # -------------------------------------------------

                    "disk": guest.disk,

                    "max_disk": guest.max_disk,

                    "disk_read": (
                        guest.disk_read
                    ),

                    "disk_write": (
                        guest.disk_write
                    ),

                    # -------------------------------------------------
                    # NETWORK
                    # -------------------------------------------------

                    "net_in": guest.net_in,

                    "net_out": guest.net_out,

                    # -------------------------------------------------
                    # RUNTIME
                    # -------------------------------------------------

                    "uptime": guest.uptime,
                }
            )

        return guests
