from atlas.collectors.base import Collector
from atlas.collectors.services.systemd import SystemServiceInfo

import subprocess


from atlas.config.proxmox import (
    require_proxmox_host,
)

IGNORED_SERVICE_PATTERNS = [

    "systemd-",
    "apt-",
    "dbus.service",
    "getty",
    "container-getty",
    "display-manager",
    "emergency",
    "rescue",
    "initrd-",
    "modprobe@",
    "kmod-",
    "plymouth",
    "e2scrub",
    "fstrim",
    "logrotate",
    "man-db",
    "dpkg",
    "syslog",
    "auditd",
    "apparmor",
    "console-",
    "wtmpdb",
    "machine-id",
    "udev",
    "vconsole",
    "random-seed",
    "tmpfiles",
    "fsck",

    "connman",
    "ifupdown",
    "exim4",
    "postfix",
    "sendmail",
    "proxmox-regenerate",
    "rc-local",
]


class LXCServiceCollector(Collector):

    name = "lxc-services"


    def __init__(
        self,
        proxmox_host=None,
    ):

        self.proxmox_host = (
            proxmox_host
            or require_proxmox_host()
        )



    def collect(
        self,
        lxc,
    ):

        vmid = str(
            lxc["vmid"]
        )


        result = subprocess.run(

            [
                "ssh",
                self.proxmox_host,
                "pct",
                "exec",
                vmid,
                "--",
                "systemctl",
                "list-units",
                "--type=service",
                "--all",
                "--no-pager",
                "--plain",
            ],

            capture_output=True,

            text=True,

        )

        if result.returncode != 0:

            detail = (
                result.stderr.strip()
                or result.stdout.strip()
                or (
                    "LXC service discovery failed "
                    f"for vmid={vmid} "
                    f"with exit code {result.returncode}"
                )
            )

            raise RuntimeError(
                detail
            )


        services = []


        for line in result.stdout.splitlines():


            if not line.strip():
                continue


            if ".service" not in line:
                continue


            parts = line.split()


            if len(parts) < 4:
                continue


            name = parts[0]


            if any(
                pattern in name
                for pattern in IGNORED_SERVICE_PATTERNS
            ):
                continue


            services.append(

                SystemServiceInfo(

                    hostname=lxc["hostname"],

                    name=parts[0],

                    status=parts[2],

                    state=parts[3],

                )

            )


        return services
