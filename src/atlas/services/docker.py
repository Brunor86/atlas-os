import logging
import time
import docker

from atlas.models.container import ContainerInfo
from atlas.models.docker import DockerInfo


logger = logging.getLogger(__name__)


class DockerService:

    def __init__(self):

        try:

            self.client = docker.from_env()

            self.client.ping()

        except Exception as exc:

            raise RuntimeError(
                "Docker daemon unavailable"
            ) from exc



    def get_info(self) -> DockerInfo:

        total_start = time.time()

        version = self.client.version()["Version"]

        daemon_info = (
            self.client.info()
            or {}
        )

        host_name = (
            daemon_info.get("Name")
            or None
        )

        t_list = time.time()

        containers_raw = self.client.containers.list(
            all=True
        )

        list_seconds = (
            time.time()
            - t_list
        )


        containers = []


        t_loop = time.time()


        for container in containers_raw:


            cpu_percent, memory_mb = self._get_stats(
                container
            )

            # ---------------------------------------------------------
            # Preserve structural metadata exposed by Docker.
            #
            # This information is discovery evidence. Interpretation
            # belongs to higher layers.
            # ---------------------------------------------------------

            attrs = (
                getattr(
                    container,
                    "attrs",
                    None,
                )
                or {}
            )

            config = (
                attrs.get(
                    "Config"
                )
                or {}
            )

            labels = dict(
                config.get(
                    "Labels"
                )
                or {}
            )

            network_settings = (
                attrs.get(
                    "NetworkSettings"
                )
                or {}
            )

            networks_raw = (
                network_settings.get(
                    "Networks"
                )
                or {}
            )

            networks = sorted(
                str(name)
                for name in networks_raw.keys()
            )

            mounts = []

            for mount in (
                attrs.get(
                    "Mounts"
                )
                or []
            ):

                if not isinstance(
                    mount,
                    dict,
                ):
                    continue

                mounts.append(
                    {
                        "type":
                            mount.get(
                                "Type"
                            ),
                        "source":
                            mount.get(
                                "Source"
                            ),
                        "destination":
                            mount.get(
                                "Destination"
                            ),
                        "mode":
                            mount.get(
                                "Mode"
                            ),
                        "rw":
                            mount.get(
                                "RW"
                            ),
                        "name":
                            mount.get(
                                "Name"
                            ),
                    }
                )

            compose_project = labels.get(
                "com.docker.compose.project"
            )

            compose_service = labels.get(
                "com.docker.compose.service"
            )


            containers.append(

                ContainerInfo(

                    id=container.short_id,

                    name=container.name,

                    image=(

                        container.image.tags[0]

                        if container.image.tags

                        else container.image.id

                    ),

                    status=container.status,


                    health=None,


                    cpu_percent=cpu_percent,


                    memory_mb=memory_mb,

                    labels=labels,

                    networks=networks,

                    mounts=mounts,

                    compose_project=compose_project,

                    compose_service=compose_service,

                )

            )


        loop_seconds = (
            time.time()
            - t_loop
        )

        total_seconds = (
            time.time()
            - total_start
        )

        logger.debug(
            (
                "Docker inventory timing "
                "list_seconds=%.3f "
                "loop_seconds=%.3f "
                "total_seconds=%.3f "
                "containers=%s"
            ),
            list_seconds,
            loop_seconds,
            total_seconds,
            len(containers),
        )


        return DockerInfo(

            version=version,

            total=len(containers),

            running=sum(

                1

                for c in containers

                if c.status == "running"

            ),

            exited=sum(

                1

                for c in containers

                if c.status == "exited"

            ),

            containers=containers,

            host_name=host_name,

        )



    def _get_stats(
        self,
        container
    ):

        """
        Las métricas dinámicas vienen de cAdvisor/Prometheus.

        El snapshot de ATLAS guarda solamente
        información estructural del contenedor.
        """

        return 0.0, 0.0
