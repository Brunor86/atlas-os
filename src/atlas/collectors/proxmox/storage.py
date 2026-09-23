import subprocess
import re

from atlas.config.proxmox import (
    require_proxmox_host,
)


class ProxmoxStorageDiscovery:


    def __init__(
        self,
        host=None,
    ):

        self.host = (
            host
            or require_proxmox_host()
        )



    def discover(self):

        result = subprocess.run(
            [
                "ssh",
                self.host,
                "ls",
                "-l",
                "/dev/disk/by-id/",
            ],
            capture_output=True,
            text=True,
        )


        output = result.stdout


        devices = []


        for line in output.splitlines():

            if "ata-" in line:

                match = re.search(
                    r"(ata-\S+)\s+->\s+\.\./\.\./(\S+)",
                    line,
                )


                if match:

                    devices.append(
                        {
                            "id": match.group(1).replace(
                                "ata-",
                                ""
                            ),

                            "path": "/dev/disk/by-id/" + match.group(1),

                            "device": "/dev/" + match.group(2),
                        }
                    )


        return devices
