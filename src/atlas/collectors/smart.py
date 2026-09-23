from __future__ import annotations

from dataclasses import dataclass
import re
import subprocess

from atlas.collectors.base import Collector


@dataclass(slots=True)
class SmartInfo:

    device: str

    model: str

    serial: str

    vendor: str | None = None

    firmware: str | None = None

    temperature: int | None = None

    power_on_hours: int | None = None

    health: str | None = None

    smart_available: bool = False

    smart_passed: bool = False



class SmartCollector(Collector):

    name = "smart"


    def __init__(self, device: str):

        self.device = device



    def collect(self) -> list[SmartInfo]:

        result = subprocess.run(
            [
                "smartctl",
                "-a",
                self.device,
            ],
            capture_output=True,
            text=True,
        )


        output = result.stdout + result.stderr


        if not output:

            raise RuntimeError(
                "smartctl returned empty output"
            )



        def search(pattern: str, default=""):

            match = re.search(
                pattern,
                output,
                re.MULTILINE
            )

            if match:

                return match.group(1).strip()


            return default



        vendor = search(
            r"Vendor:\s+(.*)"
        )


        model = search(
            r"Device Model:\s+(.*)"
        )


        if not model:

            model = search(
                r"Product:\s+(.*)"
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


        smart_available = bool(
            health
        )


        temp = None

        hours = None



        if smart_available:


            temp = search(
                r"^\s*194\s+Temperature_Celsius.*?(\d+)\s*$"
            )


            if not temp:

                temp = search(
                    r"Temperature_Celsius.*?(\d+)$"
                )


            if not temp:

                temp = search(
                    r"Current Drive Temperature:\s+(\d+)"
                )


            hours = search(
                r"^\s*9\s+Power_On_Hours.*?(\d+)\s*$"
            )



        return [

            SmartInfo(

                device=self.device,

                model=model,

                serial=serial,

                vendor=vendor,

                firmware=firmware,

                temperature=(
                    int(temp)
                    if temp
                    else None
                ),

                power_on_hours=(
                    int(hours)
                    if hours
                    else None
                ),

                health=(
                    health
                    if health
                    else None
                ),

                smart_available=smart_available,

                smart_passed=(
                    health == "PASSED"
                ),

            )

        ]
