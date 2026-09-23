from dataclasses import dataclass


@dataclass(slots=True)
class StorageInfo:

    filesystem: str
    mountpoint: str
    total_gb: float
    used_gb: float
    free_gb: float
    usage_percent: float
