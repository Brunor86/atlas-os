from dataclasses import dataclass


@dataclass(slots=True)
class SystemInfo:
    hostname: str
    os_name: str
    kernel: str
    architecture: str
    python_version: str
    uptime: str
    boot_time: str
    timezone: str
    cpu_percent: float
    cpu_cores: int
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
