from datetime import datetime

from atlas.services.infrastructure import InfrastructureService
from atlas.services.health.service import HealthService
from atlas.services.insights.service import InsightService

from atlas.services.logs.manager import LogManager

from atlas.storage.database import Database

from atlas.services.snapshots.serializer import SnapshotSerializer



from atlas.services.assets.criticality import (
    criticality_from_labels,
)

class CollectorService:


    def __init__(
        self,
    ):

        self.infrastructure = InfrastructureService()

        self.health = HealthService()

        self.insights = InsightService()

        self.logs = LogManager()

        self.database = Database()

        self.serializer = SnapshotSerializer()



    def collect(
        self,
    ):


        infra = self.infrastructure.collect()



        health = self.health.evaluate(
            infra
        )



        insights = self.insights.generate(
            infra,
            health,
        )



        containers = [

            {

                "name": container.name,

                "status": container.status,

                "criticality":
                    criticality_from_labels(
                        container.labels
                    ).name,

            }

            for container in infra.docker.containers

        ]



        logs = self.logs.analyze_containers(
            containers
        )



        snapshot = self.serializer.serialize(

            infra,

            health,

            insights,

            logs,

        )



        self.database.save_snapshot(

            datetime.now().isoformat(),

            snapshot

        )



        return {


            "infra":

                infra,


            "health":

                health,


            "insights":

                insights,


            "logs":

                logs,

        }
