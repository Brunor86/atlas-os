import os
import platform
import socket
from datetime import datetime

import psutil

from atlas.models.system import SystemInfo
from atlas.services.base import BaseService


class SystemService(BaseService):


    def _get_os_name(self) -> str:
        """
        Obtiene el nombre amigable del sistema operativo.
        """

        if os.path.exists("/etc/os-release"):

            with open("/etc/os-release") as f:

                for line in f:

                    if line.startswith("PRETTY_NAME="):

                        return (
                            line
                            .split("=")[1]
                            .strip()
                            .replace('"', "")
                        )


        return platform.platform()



    def _get_uptime(self) -> str:

        boot = datetime.fromtimestamp(
            psutil.boot_time()
        )

        delta = datetime.now() - boot

        days = delta.days

        hours = (
            delta.seconds //
            3600
        )

        return (
            f"{days} días, {hours} horas"
        )



    def get_info(self) -> SystemInfo:

        self.logger.debug(
            "Collecting system information"
        )


        boot = datetime.fromtimestamp(
            psutil.boot_time()
        )


        memory = psutil.virtual_memory()



        return SystemInfo(

            hostname=socket.gethostname(),

            os_name=self._get_os_name(),

            kernel=platform.release(),

            architecture=platform.machine(),

            python_version=platform.python_version(),

            uptime=self._get_uptime(),

            boot_time=boot.strftime(
                "%Y-%m-%d %H:%M"
            ),

            timezone=datetime.now()
            .astimezone()
            .tzname(),


            # No bloquea 1 segundo
            cpu_percent=psutil.cpu_percent(
                interval=None
            ),


            cpu_cores=psutil.cpu_count(),


            memory_percent=memory.percent,


            memory_used_gb=round(
                memory.used /
                (1024**3),
                2
            ),


            memory_total_gb=round(
                memory.total /
                (1024**3),
                2
            ),

        )
