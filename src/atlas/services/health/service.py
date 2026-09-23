
from atlas.models.health import HealthInfo
from atlas.services.health.docker_rule import DockerRule
from atlas.services.health.proxmox_rule import ProxmoxRule


class HealthService:

    def __init__(self):

        self.rules = [

            DockerRule(),

            ProxmoxRule(),

        ]


    def evaluate(
        self,
        infra=None,
        assets=None,
    ):

        health = HealthInfo(
            status="healthy",
        )


        for rule in self.rules:

            rule.evaluate(
                infra,
                health,
                assets,
            )


        return health
