from datetime import datetime, UTC

from atlas.services.noc.service import NOCService
from atlas.services.metrics import MetricsService

from atlas.services.discovery.kernel import DiscoveryKernel

from atlas.services.knowledge.service import KnowledgeService
from atlas.services.knowledge.graph import GraphService


class NOCOrchestrator:

    def __init__(self):

        self.discovery = DiscoveryKernel()

        self.registry = self.discovery.registry

        self.discovery.discover()


        #
        # Asset graph is built during discovery.
        # NOC consumes the persisted graph.
        #

        self.graph = GraphService(
            self.registry
        )


        self.knowledge = KnowledgeService(
            self.registry
        )


        self.noc = NOCService(
            registry=self.registry
        )


        self.noc.set_knowledge(
            self.knowledge,
            self.graph,
        )


        self.metrics = MetricsService()


    def analyze(
        self,
        context=None
    ):


        if context is None:

            context = {}


        report = {

            "timestamp":
                datetime.now(UTC),

            "noc":
                {},

            "metrics":
                {},

        }


        #
        # NOC analysis
        #

        report["noc"] = self.noc.generate(

            context

        )


        #
        # Metrics collection
        #

        try:

            report["metrics"] = {

                "docker_memory":
                    self.metrics.docker_memory(),

                "docker_cpu":
                    self.metrics.docker_cpu(),

            }


        except Exception as exc:

            report["metrics"] = {

                "error":
                    str(exc)

            }


        return report
