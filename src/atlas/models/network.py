from dataclasses import dataclass


@dataclass
class NetworkInterface:
    name: str
    address: str
    status: str


@dataclass
class NetworkInfo:
    hostname: str
    interfaces: list[NetworkInterface]
    gateway: str
    dns: list[str]
