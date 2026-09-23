from atlas.models.alert import Alert
from atlas.services.health.base import HealthRule
from atlas.core.asset import (
    AssetStatus,
    AssetType,
)


class DockerRule(HealthRule):

    def evaluate(
        self,
        infra,
        health,
        assets=None,
    ):

        stopped = []


        docker = (
            getattr(
                infra,
                "docker",
                None,
            )
            if infra
            else None
        )


        if (
            docker is not None
            and getattr(
                docker,
                "available",
                True,
            )
            is False
        ):

            if health.status == "healthy":
                health.status = "warning"


            health.alerts.append(
                Alert(
                    severity="warning",
                    source="docker",
                    title="Docker unavailable",
                    message=(
                        getattr(
                            docker,
                            "error",
                            None,
                        )
                        or (
                            "Docker provider "
                            "is unavailable"
                        )
                    ),
                    affected_assets=[],
                )
            )

            # Do not interpret previously observed container state
            # while the authoritative Docker provider is unavailable.
            return


        #
        # Asset Registry path
        #

        if assets:

            for asset in assets:

                if asset.type != AssetType.APPLICATION:
                    continue


                metadata = (
                    asset.metadata
                    or {}
                )

                #
                # Docker provider owns runtime-specific state.
                # Upper health semantics consume the normalized
                # Asset status plus provider evidence.
                #
                if metadata.get(
                    "runtime"
                ) != "docker":
                    continue

                docker_status = (
                    str(
                        metadata.get(
                            "docker_status",
                            "",
                        )
                    )
                    .strip()
                    .lower()
                )

                if (
                    asset.status
                    == AssetStatus.OFFLINE
                    or docker_status
                    in (
                        "exited",
                        "stopped",
                        "dead",
                    )
                ):

                    stopped.append(
                        asset
                    )


        #
        # Legacy infrastructure path
        #

        if not stopped and infra:

            docker = getattr(
                infra,
                "docker",
                None,
            )

            if docker and docker.exited > 0:

                stopped = [

                    c

                    for c in docker.containers

                    if c.status == "exited"

                ]


        if not stopped:
            return


        if health.status == "healthy":

            health.status = "warning"


        names = [

            getattr(
                item,
                "name",
                "unknown",
            )

            for item in stopped

        ]


        health.alerts.append(

            Alert(

                severity="warning",

                source="docker",

                title="Stopped containers",

                message=(
                    f"{len(stopped)} container(s) stopped: "
                    +
                    ", ".join(names)
                ),

                affected_assets=[
                    str(item.id)
                    for item in stopped
                    if getattr(
                        item,
                        "id",
                        None,
                    )
                ],

            )

        )
