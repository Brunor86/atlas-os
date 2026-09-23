import socket
import subprocess

import psutil

from atlas.models.network import (
    NetworkInfo,
    NetworkInterface,
)


class NetworkService:

    def get_info(self) -> NetworkInfo:

        hostname = socket.gethostname()

        interfaces = []

        addresses = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for name, addr_list in addresses.items():

            status = "DOWN"

            if name in stats and stats[name].isup:
                status = "UP"

            for addr in addr_list:

                if addr.family.name == "AF_INET":

                    interfaces.append(
                        NetworkInterface(
                            name=name,
                            address=addr.address,
                            status=status,
                        )
                    )

        gateway = self._get_gateway()

        dns = self._get_dns()

        return NetworkInfo(
            hostname=hostname,
            interfaces=interfaces,
            gateway=gateway,
            dns=dns,
        )


    def _get_gateway(self):

        try:
            result = subprocess.check_output(
                ["ip", "route"],
                text=True
            )

            for line in result.splitlines():

                if line.startswith("default"):

                    return line.split()[2]

        except Exception:
            pass

        return "unknown"


    def _get_dns(self):

        dns = []

        try:

            with open("/etc/resolv.conf") as file:

                for line in file:

                    if line.startswith("nameserver"):

                        dns.append(
                            line.split()[1]
                        )

        except Exception:
            pass

        return dns
