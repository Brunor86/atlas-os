"""
Declarative routing metadata for ATLAS Intelligence tools.

This module contains tool-specific vocabulary, not routing logic.

AIService must remain unaware of concrete tool names or
infrastructure-specific keywords.
"""


TOOL_ROUTING_HINTS = {

    "telemetry_system": (
        "uso cpu",
        "carga cpu",
        "cpu usage",
        "carga sistema",
        "system load",
        "memoria ram",
        "uso ram",
        "ram usage",
        "swap",
    ),

    "telemetry_temperatures": (
        "sensores temperatura",
        "temperaturas hardware",
        "temperaturas sistema",
        "hardware temperatures",
        "temperature sensors",
    ),

    "telemetry_filesystems": (
        "filesystem",
        "sistema de archivos",
        "espacio filesystem",
        "espacio libre filesystem",
        "capacidad filesystem",
        "particion",
        "partición",
    ),

    "telemetry_smart": (
        "smart",
        "estado smart",
        "salud smart",
        "salud del disco",
        "salud disco",
        "temperatura del disco",
        "temperatura disco",
        "temperatura hdd",
        "temperatura del hdd",
        "temperatura ssd",
        "temperatura del ssd",
        "temperatura nvme",
        "temperatura del nvme",
        "disk temperature",
        "disk health",
        "smart health",
        "power on hours",
    ),

    "telemetry_proxmox_cpu_temperature": (
        "temperatura cpu",
        "temperatura del cpu",
        "temperatura procesador",
        "temperatura del procesador",
        "cpu temperature",
        "processor temperature",
        "temperatura cpu proxmox",
    ),

    "telemetry_proxmox_storage": (
        "almacenamiento proxmox",
        "storage proxmox",
        "espacio libre proxmox",
        "espacio disponible proxmox",
        "capacidad proxmox",
        "capacidad almacenamiento",
        "thin pool",
        "thin-pool",
        "thinpool",
        "lvm",
        "capacidad nvme",
    ),

    "telemetry_processes": (
        "procesos",
        "procesos corriendo",
        "procesos activos",
        "running processes",
        "uso cpu proceso",
        "uso memoria proceso",
        "proceso cpu",
        "proceso memoria",
    ),

    "telemetry_network": (
        "red",
        "interfaces de red",
        "interfaces red",
        "network interfaces",
        "direcciones ip",
        "direccion ip",
        "tráfico red",
        "trafico red",
        "conexiones de red",
        "conexiones red",
        "conexiones activas",
    ),

    "telemetry_path_size": (
        "tamaño archivo",
        "tamano archivo",
        "tamaño directorio",
        "tamano directorio",
        "espacio carpeta",
        "espacio directorio",
        "directory size",
        "file size",
    ),

    "telemetry_atlas_database_size": (
        "tamaño base atlas",
        "tamano base atlas",
        "tamaño base de datos atlas",
        "tamano base de datos atlas",
        "espacio base atlas",
        "atlas database size",
    ),
}


def get_tool_routing_hints(
    tool_name: str,
) -> tuple[str, ...]:
    """
    Return routing vocabulary declared for a tool.

    Missing metadata is valid. The generic AI router will simply
    leave the full tool catalog available.
    """

    return TOOL_ROUTING_HINTS.get(
        tool_name,
        (),
    )
