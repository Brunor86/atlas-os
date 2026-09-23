from __future__ import annotations

from atlas.services.intelligence.operator_tools.base import (
    ToolDefinition,
    ToolResult,
)
from atlas.services.telemetry import TelemetryService


class TelemetryTools:

    def __init__(
        self,
        telemetry: TelemetryService | None = None,
    ):

        self.telemetry = (
            telemetry
            or TelemetryService()
        )

    def system(self) -> ToolResult:

        try:

            return ToolResult(
                tool="telemetry_system",
                status="SUCCESS",
                result=self.telemetry.system(),
                evidence=[
                    "system telemetry collected locally"
                ],
            )

        except Exception as exc:

            return ToolResult(
                tool="telemetry_system",
                status="ERROR",
                error=str(exc),
            )

    def temperatures(self) -> ToolResult:

        try:

            result = (
                self.telemetry.temperatures()
            )

            return ToolResult(
                tool="telemetry_temperatures",
                status="SUCCESS",
                result=result,
                evidence=[
                    f"{len(result)} temperature sensors detected"
                ],
            )

        except Exception as exc:

            return ToolResult(
                tool="telemetry_temperatures",
                status="ERROR",
                error=str(exc),
            )

    def filesystems(self) -> ToolResult:

        try:

            result = (
                self.telemetry.filesystems()
            )

            return ToolResult(
                tool="telemetry_filesystems",
                status="SUCCESS",
                result=result,
                evidence=[
                    f"{len(result)} filesystems inspected"
                ],
            )

        except Exception as exc:

            return ToolResult(
                tool="telemetry_filesystems",
                status="ERROR",
                error=str(exc),
            )

    def smart(
        self,
        device: str | None = None,
    ) -> ToolResult:

        try:

            result = self.telemetry.smart(
                device
            )

            return ToolResult(
                tool="telemetry_smart",
                status="SUCCESS",
                result=result,
                evidence=[
                    f"{len(result)} SMART records collected"
                ],
            )

        except Exception as exc:

            return ToolResult(
                tool="telemetry_smart",
                status="ERROR",
                error=str(exc),
            )

    def processes(
        self,
        limit: int = 20,
    ) -> ToolResult:

        try:

            result = self.telemetry.processes(
                limit
            )

            return ToolResult(
                tool="telemetry_processes",
                status="SUCCESS",
                result=result,
                evidence=[
                    f"top {len(result)} processes collected"
                ],
            )

        except Exception as exc:

            return ToolResult(
                tool="telemetry_processes",
                status="ERROR",
                error=str(exc),
            )

    def network(
        self,
    ) -> ToolResult:

        try:

            result = {
                "interfaces":
                    self.telemetry.network_interfaces(),

                "connections":
                    self.telemetry.network_connections(),
            }

            return ToolResult(
                tool="telemetry_network",
                status="SUCCESS",
                result=result,
                evidence=[
                    "network telemetry collected locally"
                ],
            )

        except Exception as exc:

            return ToolResult(
                tool="telemetry_network",
                status="ERROR",
                error=str(exc),
            )

    def path_size(
        self,
        path: str,
    ) -> ToolResult:

        try:

            result = self.telemetry.path_size(
                path
            )

            return ToolResult(
                tool="telemetry_path_size",
                status="SUCCESS",
                result=result,
                evidence=[
                    f"path size calculated for {path}"
                ],
            )

        except FileNotFoundError:

            return ToolResult(
                tool="telemetry_path_size",
                status="NOT_FOUND",
                error=f"Path not found: {path}",
            )

        except Exception as exc:

            return ToolResult(
                tool="telemetry_path_size",
                status="ERROR",
                error=str(exc),
            )

    def atlas_database_size(
        self,
        database_path: str = "atlas.db",
    ) -> ToolResult:

        try:

            result = (
                self.telemetry.atlas_database_size(
                    database_path
                )
            )

            return ToolResult(
                tool="telemetry_atlas_database_size",
                status="SUCCESS",
                result=result,
                evidence=[
                    "ATLAS database size calculated"
                ],
            )

        except Exception as exc:

            return ToolResult(
                tool="telemetry_atlas_database_size",
                status="ERROR",
                error=str(exc),
            )


    def proxmox_cpu_temperature(self) -> ToolResult:

        try:

            result = (
                self.telemetry.proxmox_cpu_temperature()
            )

            return ToolResult(
                tool="telemetry_proxmox_cpu_temperature",
                status="SUCCESS",
                result=result,
                evidence=[
                    "Proxmox k10temp sensor inspected"
                ],
            )

        except Exception as exc:

            return ToolResult(
                tool="telemetry_proxmox_cpu_temperature",
                status="ERROR",
                error=str(exc),
            )


    def proxmox_storage(self) -> ToolResult:

        try:

            result = (
                self.telemetry.proxmox_storage()
            )

            return ToolResult(
                tool="telemetry_proxmox_storage",
                status="SUCCESS",
                result=result,
                evidence=[
                    "Proxmox physical storage inspected"
                ],
            )

        except Exception as exc:

            return ToolResult(
                tool="telemetry_proxmox_storage",
                status="ERROR",
                error=str(exc),
            )


    def definitions(self) -> list[ToolDefinition]:

        return [

            ToolDefinition(
                name="telemetry_system",
                description=(
                    "Read physical system telemetry including "
                    "CPU usage, CPU cores, frequency, RAM, "
                    "swap and load."
                ),
                handler=self.system,
                read_only=True,
                requires_approval=False,
                capabilities=(
                    "CPU",
                    "MEMORY",
                    "SYSTEM",
                ),
            ),

            ToolDefinition(
                name="telemetry_temperatures",
                description=(
                    "Read hardware temperature sensors "
                    "available from the operating system."
                ),
                handler=self.temperatures,
                read_only=True,
                requires_approval=False,
                capabilities=(
                    "TEMPERATURE",
                ),
            ),

            ToolDefinition(
                name="telemetry_filesystems",
                description=(
                    "Read filesystem capacity, used space "
                    "and free space."
                ),
                handler=self.filesystems,
                read_only=True,
                requires_approval=False,
                capabilities=(
                    "STORAGE",
                ),
            ),

            ToolDefinition(
                name="telemetry_smart",
                description=(
                    "Read PHYSICAL DISK SMART telemetry. Routing aliases: temperatura disco, temperatura del disco, temperatura HDD, temperatura SSD, temperatura NVMe, salud disco, salud del disco, estado SMART, errores disco, horas encendido disco.  "
                    "Use this tool for questions about physical disk "
                    "temperature, SMART health, disk health, power-on "
                    "hours, SMART status, disk errors or the condition "
                    "of a specific physical disk such as /dev/sdb, "
                    "including a 12TB HDD. "
                    "If the user asks for the temperature of a physical "
                    "disk, ALWAYS prefer this tool. "
                    "Do NOT use telemetry_proxmox_storage for disk "
                    "temperature questions. "
                    "Do NOT use it for filesystem capacity, LVM, "
                    "thin-pool or free-space questions."
                ),
                handler=self.smart,
                read_only=True,
                requires_approval=False,
                capabilities=(
                    "SMART",
                    "TEMPERATURE",
                    "STORAGE",
                ),
            ),

            ToolDefinition(
                name="telemetry_proxmox_cpu_temperature",
                description=(
                    "Read the physical CPU temperature "
                    "of the Proxmox host using the "
                    "k10temp hardware sensor."
                ),
                handler=self.proxmox_cpu_temperature,
                read_only=True,
                requires_approval=False,
                capabilities=(
                    "TEMPERATURE",
                    "CPU",
                ),
            ),

            ToolDefinition(
                name="telemetry_proxmox_storage",
                description=(
                    "Read Proxmox storage CAPACITY information, "
                    "including NVMe disks, LVM capacity and "
                    "remaining thin-pool space. "
                    "This tool does NOT provide physical disk "
                    "temperature or SMART health. "
                    "For disk temperature or SMART questions, "
                    "use telemetry_smart instead."
                ),
                handler=self.proxmox_storage,
                read_only=True,
                requires_approval=False,
                capabilities=(
                    "STORAGE",
                ),
            ),


            ToolDefinition(
                name="telemetry_processes",
                description=(
                    "Read running processes and their CPU "
                    "and memory usage."
                ),
                handler=self.processes,
                read_only=True,
                requires_approval=False,
                capabilities=(
                    "PROCESS",
                ),
            ),

            ToolDefinition(
                name="telemetry_network",
                description=(
                    "Read network interfaces, IP addresses, "
                    "traffic counters and active connections."
                ),
                handler=self.network,
                read_only=True,
                requires_approval=False,
                capabilities=(
                    "NETWORK",
                ),
            ),

            ToolDefinition(
                name="telemetry_path_size",
                description=(
                    "Calculate how much disk space a file "
                    "or directory uses."
                ),
                handler=self.path_size,
                read_only=True,
                requires_approval=False,
                capabilities=(
                    "STORAGE",
                ),
            ),

            ToolDefinition(
                name="telemetry_atlas_database_size",
                description=(
                    "Calculate the disk space currently "
                    "used by the ATLAS database."
                ),
                handler=self.atlas_database_size,
                read_only=True,
                requires_approval=False,
                capabilities=(
                    "STORAGE",
                    "DATABASE",
                ),
            ),
        ]


# ------------------------------------------------------------
# Backward compatibility
#
# Canonical implementation:
#     TelemetryTools.definitions()
#
# This wrapper keeps existing imports working.
# ------------------------------------------------------------

def build_telemetry_tools(
    telemetry: TelemetryService | None = None,
) -> list[ToolDefinition]:

    tools = TelemetryTools(
        telemetry=telemetry,
    )

    return tools.definitions()
