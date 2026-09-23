import os
import shutil

from atlas.core.asset import (
    Asset,
    AssetStatus,
    AssetType,
    Capability,
    Criticality,
    health_from_status,
)

from atlas.core.provider import AssetProvider
from atlas.core.identity import AssetIdentity
from atlas.core.identity_resolver import generate_asset_id
from atlas.core.semantic import SemanticGroup

from atlas.services.docker import DockerService


from atlas.services.assets.criticality import (
    criticality_from_labels,
)

class DockerAssetProvider(AssetProvider):

    @staticmethod
    def is_configured() -> bool:
        """
        Return whether this host presents evidence of a Docker runtime.

        Docker is optional in a public ATLAS installation.

        No CLI and no local socket means Docker is simply not configured.
        Partial presence still counts as configured so an unhealthy Docker
        installation remains visible as a provider failure instead of being
        silently ignored.
        """

        docker_cli = shutil.which(
            "docker"
        )

        socket_present = os.path.exists(
            "/var/run/docker.sock"
        )

        return bool(
            docker_cli
            or socket_present
        )

    def __init__(
        self,
        service=None,
    ):
        # Do not contact Docker while DiscoveryKernel is being built.
        #
        # Provider construction must be safe even when Docker is absent.
        # The actual connection belongs to the collect boundary where
        # DiscoveryKernel can isolate provider failures.
        self.service = service

    def collect(self) -> list[Asset]:

        if self.service is None:
            self.service = DockerService()

        docker_info = self.service.get_info()

        assets = []

        for container in docker_info.containers:

            status = AssetStatus.UNKNOWN

            if container.status == "running":
                status = AssetStatus.ONLINE

            elif container.status == "exited":
                status = AssetStatus.OFFLINE

            else:
                status = AssetStatus.DEGRADED

            image = getattr(
                container,
                "image",
                None,
            )

            identity = AssetIdentity(
                serial=container.name,
                vendor="Docker",
            )

            semantic_groups = []

            #
            # Provider boundary:
            #
            # Docker understands Compose.
            # The rest of ATLAS does not need to.
            #
            # Translate the native Compose project into the generic
            # ATLAS grouping contract discovered from runtime data.
            #
            if container.compose_project:

                semantic_groups.append(
                    SemanticGroup(
                        kind="application_stack",
                        value=str(
                            container.compose_project
                        ),
                        scope=str(
                            docker_info.host_name
                        ),
                        source="docker_compose",
                        confidence=1.0,
                    ).as_dict()
                )

            asset = Asset(
                id=generate_asset_id(
                    "application",
                    identity,
                ),
                name=container.name,
                type=AssetType.APPLICATION,
                identity=identity,
                status=status,
                metadata={
                    "container_name": container.name,
                    "container_id": container.id,
                    "docker_id": container.id,
                    "docker_status": container.status,
                    "image": image,

                    # Structural Docker discovery evidence.
                    "runtime": "docker",

                    # Runtime ownership discovered from Docker itself.
                    # RoleInference._belongs_to() consumes this
                    # generically; no host name is hardcoded.
                    "docker_host":
                        docker_info.host_name,

                    "labels": (
                        container.labels
                        or {}
                    ),
                    "networks": (
                        container.networks
                        or []
                    ),
                    "mounts": (
                        container.mounts
                        or []
                    ),
                    "compose_project":
                        container.compose_project,
                    "compose_service":
                        container.compose_service,

                    # Technology-neutral semantic facets.
                    #
                    # Upper layers consume this field rather than
                    # Docker-specific compose_project semantics.
                    "semantic_groups":
                        semantic_groups,
                },
                health=health_from_status(
                    status
                ),

                criticality=criticality_from_labels(
                    container.labels
                ),
                capabilities={
                    Capability.START,
                    Capability.STOP,
                    Capability.RESTART,
                    Capability.LOGS,
                },
            )

            assets.append(asset)

        return assets
