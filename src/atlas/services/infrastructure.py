import logging
from concurrent.futures import ThreadPoolExecutor

from atlas.core.infrastructure import Infrastructure

from atlas.models.docker import DockerInfo
from atlas.models.proxmox import ProxmoxInfo

from atlas.services.system import SystemService
from atlas.services.docker import DockerService
from atlas.services.storage import StorageService
from atlas.services.network import NetworkService
from atlas.services.proxmox import ProxmoxService


logger = logging.getLogger(__name__)


class InfrastructureService:

    @staticmethod
    def _provider_error(
        exc,
    ) -> str:

        value = (
            type(exc).__name__
            + ": "
            + str(exc)
        ).strip()

        # Keep persisted operational evidence bounded.
        return value[:512]


    def _docker_unavailable(
        self,
        exc,
    ) -> DockerInfo:

        error = self._provider_error(
            exc
        )

        logger.warning(
            "Docker provider unavailable: %s",
            error,
        )

        return DockerInfo(
            version="unavailable",
            total=0,
            running=0,
            exited=0,
            containers=[],
            host_name=None,
            available=False,
            error=error,
        )


    def _proxmox_unavailable(
        self,
        exc,
    ) -> ProxmoxInfo:

        error = self._provider_error(
            exc
        )

        logger.warning(
            "Proxmox provider unavailable: %s",
            error,
        )

        return ProxmoxInfo(
            version="unavailable",
            release="",
            node="unknown",
            node_info=None,
            guests=[],
            available=False,
            error=error,
        )


    def collect(
        self,
    ) -> Infrastructure:

        # Providers are instantiated lazily inside their worker.
        #
        # This matters because DockerService and ProxmoxService can
        # fail during __init__. A constructor failure must belong to
        # that provider, not abort service-table construction.
        services = {
            "system":
                lambda:
                    SystemService().get_info(),

            "docker":
                lambda:
                    DockerService().get_info(),

            "storage":
                lambda:
                    StorageService().get_info(),

            "network":
                lambda:
                    NetworkService().get_info(),

            "proxmox":
                lambda:
                    ProxmoxService().get_info(),
        }


        results = {}


        with ThreadPoolExecutor(
            max_workers=5
        ) as executor:

            futures = {
                name:
                    executor.submit(
                        operation
                    )

                for name, operation
                in services.items()
            }


            for name, future in futures.items():

                try:

                    results[name] = (
                        future.result()
                    )

                except Exception as exc:

                    # Docker and Proxmox are external control planes.
                    #
                    # Losing one does NOT prove that its previously
                    # known assets disappeared. Preserve an explicit
                    # unavailable provider state instead.
                    if name == "docker":

                        results[name] = (
                            self._docker_unavailable(
                                exc
                            )
                        )

                        continue


                    if name == "proxmox":

                        results[name] = (
                            self._proxmox_unavailable(
                                exc
                            )
                        )

                        continue


                    # Local host truth remains fail-closed.
                    #
                    # If system/storage/network collection fails,
                    # ATLAS must not fabricate a healthy host.
                    raise


        return Infrastructure(
            system=results["system"],
            docker=results["docker"],
            storage=results["storage"],
            network=results["network"],
            proxmox=results["proxmox"],
        )
