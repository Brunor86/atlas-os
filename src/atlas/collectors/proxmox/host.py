from atlas.services.proxmox import ProxmoxService


class ProxmoxHostDiscovery:

    def __init__(self, host=None):

        self.proxmox = ProxmoxService()

    def discover(self):

        info = self.proxmox.get_info()

        if info.node_info:

            node = info.node_info

            return {
                "hostname": node.node,

                "vendor": "Proxmox",

                "status": node.status,

                # CPU
                "cpu": node.cpu,

                "max_cpu": node.max_cpu,

                # MEMORY
                "memory": node.memory,

                "max_memory": (
                    node.max_memory
                ),

                # DISK
                "disk": node.disk,

                "max_disk": (
                    node.max_disk
                ),

                # RUNTIME
                "uptime": node.uptime,
            }

        return {
            "hostname": info.node,

            "vendor": "Proxmox",

            "status": "unknown",

            "cpu": 0,

            "max_cpu": 0,

            "memory": 0,

            "max_memory": 0,

            "disk": 0,

            "max_disk": 0,

            "uptime": 0,
        }
