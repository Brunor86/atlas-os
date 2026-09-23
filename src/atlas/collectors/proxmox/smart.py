from atlas.collectors.base import Collector
from atlas.collectors.smart import SmartInfo

import subprocess
import re


class ProxmoxSmartCollector(Collector):

    name = "proxmox-smart"


    def __init__(
        self,
        host: str,
        device: str,
    ):
        self.host = host
        self.device = device



    def collect(self):

        result = subprocess.run(
            [
                "ssh",
                self.host,
                "smartctl",
                "-a",
                self.device,
            ],
            capture_output=True,
            text=True,
        )


        #
        # ssh itself uses 255 for connection / transport failures.
        #
        # Do not require returncode == 0 here because smartctl uses
        # its exit status as a diagnostic bitmask. A disk reporting
        # SMART degradation can legitimately return non-zero while
        # still providing authoritative identity and health data.
        #
        if result.returncode == 255:

            detail = (
                result.stderr.strip()
                or result.stdout.strip()
                or "SSH transport failure"
            )

            raise RuntimeError(
                f"Proxmox SMART SSH failed: {detail}"
            )

        output = result.stdout + result.stderr


        def search(pattern):

            match = re.search(
                pattern,
                output,
                re.MULTILINE
            )

            if match:
                return match.group(1).strip()

            return ""



        model = search(
            r"Device Model:\s+(.*)"
        )

        serial = search(
            r"Serial Number:\s+(.*)"
        )

        firmware = search(
            r"Firmware Version:\s+(.*)"
        )

        health = search(
            r"SMART overall-health self-assessment test result:\s+(\w+)"
        )

        #
        # A remote command that ran but produced no usable drive
        # identity is not authoritative inventory.
        #
        # This also catches cases such as smartctl missing remotely,
        # permission/device-open failures, or otherwise unusable
        # command output without confusing genuine SMART warnings
        # with Discovery failures.
        #
        if not model and not serial:

            detail = (
                result.stderr.strip()
                or result.stdout.strip()
                or (
                    "no SMART identity returned "
                    f"(exit code {result.returncode})"
                )
            )

            raise RuntimeError(
                f"Proxmox SMART unavailable: {detail}"
            )

        temperature = search(
            r"194 Temperature_Celsius.*?(\d+)$"
        )

        hours = search(
            r"9 Power_On_Hours.*?(\d+)$"
        )


        return [
            SmartInfo(
                device=self.device,
                model=model,
                serial=serial,
                vendor="WDC",
                firmware=firmware,
                temperature=(
                    int(temperature)
                    if temperature
                    else None
                ),
                power_on_hours=(
                    int(hours)
                    if hours
                    else None
                ),
                health=health,
                smart_available=bool(health),
                smart_passed=(
                    health == "PASSED"
                ),
            )
        ]
