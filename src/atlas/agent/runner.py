from atlas.collectors.registry import CollectorRegistry
from atlas.agent.report import AgentReport

from atlas.services.assets.builder import AssetBuilder
from atlas.services.assets.persistence import AssetPersistenceService
from atlas.services.observations.smart import SmartObservationBuilder

from atlas.services.noc.asset_health import AssetHealthAnalyzer
from atlas.storage.health_repository import HealthFindingRepository

from atlas.services.history.service import HistoryService



class AgentRunner:


    def __init__(
        self,
        agent_id,
        hostname,
    ):

        self.registry = CollectorRegistry()


        self.report = AgentReport(
            agent_id=agent_id,
            hostname=hostname,
        )


        self.asset_builder = AssetBuilder()

        self.asset_persistence = AssetPersistenceService()


        self.observation_builder = SmartObservationBuilder()



        self.health_analyzer = AssetHealthAnalyzer()


        self.health_repository = HealthFindingRepository()


        #
        # Historical memory
        #
        self.history_service = HistoryService()



    def add_collector(
        self,
        collector,
    ):

        self.registry.register(
            collector
        )



    def discover(
        self,
    ):

        results = self.registry.collect_all()



        for item in results:


            asset = self.asset_builder.from_smart(
                item
            )



            observations = self.observation_builder.build(
                asset.id,
                item
            )



            for obs in observations:

                asset.add_observation(
                    obs
                )





            #
            # Analyze health
            #
            findings = self.health_analyzer.analyze(
                asset
            )

            asset.health = self.health_analyzer.evaluate_health(
                asset,
                findings,
            )


            #
            # Persist current asset state.
            #
            # Health must be evaluated before persistence so the
            # Asset Registry stores the final calculated health.
            #
            self.asset_persistence.persist(
                asset
            )


            #
            # Persist historical state after health evaluation.
            #
            self.history_service.persist(
                asset
            )


            #
            # Persist health findings.
            #
            for finding in findings:

                self.health_repository.save(
                    finding
                )



            self.report.add_asset(
                asset
            )



        return self.report
