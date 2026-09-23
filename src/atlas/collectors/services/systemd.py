from dataclasses import dataclass
import subprocess

from atlas.collectors.base import Collector


@dataclass(slots=True)
class SystemServiceInfo:

    name: str

    status: str

    state: str

    hostname: str



class SystemdServiceCollector(Collector):

    name = "systemd-services"


    IGNORED_PREFIXES = [

        "systemd-",
        "apt-",
        "dpkg-",
        "modprobe",
        "getty",
        "console",
        "initrd-",
        "plymouth",
        "kmod-",
        "e2scrub",

    ]


    IGNORED_SERVICES = {

        "cron.service",
        "dbus.service",
        "logrotate.service",
        "man-db.service",

        "apparmor.service",
        "auditd.service",
        "connman.service",
        "display-manager.service",
        "emergency.service",
        "fstrim.service",
        "grub-common.service",
        "ifupdown-pre.service",
        "kbd.service",
        "keyboard-setup.service",
        "ldconfig.service",
        "rc-local.service",
        "rescue.service",
        "sshd-keygen.service",
        "sshd@sshd-keygen.service",
        "syslog.service",
        "user-runtime-dir@1000.service",
        "user@1000.service",
        "wtmpdb-update-boot.service",
        "ifup@ens18.service",

    }


    def collect(self):

        result = subprocess.run(

            [
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
                    "systemctl list-units failed "
                    f"with exit code {result.returncode}"
                )
            )

            raise RuntimeError(
                detail
            )


        services = []


        hostname = subprocess.run(
            [
                "hostname",
            ],
            capture_output=True,
            text=True,
        ).stdout.strip()


        for line in result.stdout.splitlines():

            if not line.strip():
                continue


            if (
                ".service" not in line
            ):
                continue


            parts = line.split()


            if len(parts) < 4:
                continue


            name = parts[0]


            if name in self.IGNORED_SERVICES:
                continue


            if any(
                name.startswith(prefix)
                for prefix in self.IGNORED_PREFIXES
            ):
                continue


            load = parts[1]

            active = parts[2]

            sub = parts[3]


            services.append(

                SystemServiceInfo(

                    name=name,

                    status=active,

                    state=sub,

                    hostname=hostname,

                )

            )


        return services
