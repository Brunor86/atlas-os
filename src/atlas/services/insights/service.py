
from atlas.models.insight import Insight
from atlas.core.asset import AssetType


class InsightService:


    def generate(
        self,
        infra=None,
        health=None,
        assets=None,
    ):

        insights = []


        #
        # Estado general
        #

        if health.status == "healthy":

            insights.append(

                Insight(

                    title="Infrastructure Healthy",

                    summary="No critical issues were detected.",

                    severity="info",

                )

            )


        elif health.status == "warning":

            insights.append(

                Insight(

                    title="Infrastructure Warning",

                    summary="The infrastructure is operational but requires attention.",

                    severity="warning",

                )

            )


        else:

            insights.append(

                Insight(

                    title="Infrastructure Critical",

                    summary="Critical issues require immediate attention.",

                    severity="critical",

                )

            )



        #
        # Docker / Asset Registry
        #

        stopped = []


        if assets:

            for asset in assets:

                if asset.type not in (
                    AssetType.APPLICATION,
                    AssetType.CONTAINER,
                ): 

                    continue


                state = asset.metadata.get(
                    "state"
                )


                if state in (
                    "exited",
                    "stopped",
                    "dead",
                ):

                    stopped.append(
                        asset
                    )



        #
        # Legacy snapshot fallback
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



        if stopped:

            insights.append(

                Insight(

                    title="Docker",

                    summary=(
                        f"{len(stopped)} container(s) are stopped: "
                        +
                        ", ".join(
                            a.name
                            for a in stopped
                        )
                    ),

                    severity="warning",

                      asset_id=(
                          stopped[0].id
                          if stopped
                          else None
                      ),

                )

            )

        else:

            insights.append(

                Insight(

                    title="Docker",

                    summary="All containers are running.",

                    severity="info",

                )

            )



        #
        # Storage / Memory
        # Mantener legacy por ahora
        #

        if infra:

            for disk in infra.storage:

                if disk.usage_percent >= 90:

                    insights.append(

                        Insight(

                            title="Storage",

                            summary=(
                                f"{disk.mountpoint} "
                                f"is almost full "
                                f"({disk.usage_percent:.1f}%)."
                            ),

                            severity="critical",

                        )

                    )


            if infra.system.memory_percent >= 85:

                insights.append(

                    Insight(

                        title="Memory",

                        summary=(
                            f"Memory usage is high "
                            f"({infra.system.memory_percent:.1f}%)."
                        ),

                        severity="warning",

                    )

                )


        return insights
