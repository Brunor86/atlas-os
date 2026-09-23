from atlas.storage.database import Database
from atlas.storage.event_repository import EventRepository
from atlas.storage.repository import SnapshotRepository
from atlas.storage.asset_repository import AssetRepository
from atlas.storage.health_repository import HealthFindingRepository
from atlas.storage.history_repository import HistoryRepository


from atlas.services.events.analytics import EventAnalytics
from atlas.services.events.correlation import EventCorrelation

from atlas.services.ai.recommender import AIRecommender
from atlas.services.ai.reasoning import AIReasoningEngine
from atlas.services.ai.change_detector import ChangeDetector

from atlas.services.git.service import GitService

from atlas.services.history.analyzer import HistoryAnalyzer

from atlas.services.intelligence.service import IntelligenceService
from atlas.services.ai.health import AIRuntimeHealth



class AIContextBuilder:


    def __init__(
        self,
    ):


        self.database = Database()

        self.events = EventRepository()

        self.snapshots = SnapshotRepository()

        self.assets = AssetRepository()

        self.health = HealthFindingRepository()

        self.history = HistoryRepository()


        self.analytics = EventAnalytics()

        self.correlation = EventCorrelation()

        self.recommender = AIRecommender()

        self.reasoning = AIReasoningEngine()

        self.git = GitService()

        self.change_detector = ChangeDetector()

        self.history_analyzer = HistoryAnalyzer()

        self.intelligence = IntelligenceService()





    def add_ai_runtime(
        self,
        runtime,
    ):

        self.ai_runtime = AIRuntimeHealth(
            runtime
        )


    def build(
        self,
    ):


        latest = self.snapshots.get_latest()


        active_events = self.database.get_active_events()


        active_findings = self.health.get_active()


        assets = self.assets.get_all_assets()



        incidents = self.correlation.analyze(
            active_events
        )



        recommendations = self.recommender.analyze(
            incidents
        )



        snapshot = (

            latest["data"]

            if latest

            else None

        )



        logs = (

            snapshot.get(
                "logs",
                []
            )

            if snapshot

            else []

        )



        inventory = []


        for asset in assets:


            history = self.history.get_history(
                asset.id,
                5,
            )


            history_analysis = []


            # --------------------------------------------------------
            # Asset intelligence
            #
            # AssetRepository already resolves:
            #   - capabilities
            #   - inferred roles
            #   - role confidence/evidence
            #   - metadata
            #   - relationships
            #
            # The AI context must expose that existing intelligence
            # instead of maintaining a second parallel representation.
            # --------------------------------------------------------

            observations = self.assets.get_observations(
                asset.id
            )[-10:]


            serialized_relationships = [

                {
                    "source":
                        relationship.source,

                    "target":
                        relationship.target,

                    "type":
                        relationship.type.name,

                    "confidence":
                        relationship.confidence,

                    "evidence":
                        list(
                            relationship.evidence
                        ),

                    "metadata":
                        dict(
                            relationship.metadata
                        ),

                    "created_at":
                        relationship.created_at.isoformat(),

                }

                for relationship
                in asset.relationships

            ]


            inventory.append(

                {
                    "id": asset.id,

                    "name": asset.name,

                    "type": asset.type.name,

                    "status": asset.status.name,

                    "health": asset.health,

                    "criticality":
                        asset.criticality.name,


                    # ------------------------------------------------
                    # Service classification
                    # ------------------------------------------------

                    "service":
                    {
                        "role":
                            asset.service_role.name,

                        "importance":
                            asset.service_importance.name,

                    },


                    # ------------------------------------------------
                    # Operational roles
                    # ------------------------------------------------

                    "roles":
                    {
                        "primary":
                            asset.primary_role.name,

                        "inferred":
                        sorted(
                            role.name
                            for role
                            in asset.asset_roles
                        ),

                        "confidence":
                            asset.role_confidence,

                        "evidence":
                            list(
                                asset.role_evidence
                            ),

                    },


                    # ------------------------------------------------
                    # Safe action capabilities
                    # ------------------------------------------------

                    "capabilities":
                    sorted(
                        capability.name
                        for capability
                        in asset.capabilities
                    ),


                    # ------------------------------------------------
                    # Persistent metadata
                    # ------------------------------------------------

                    "metadata":
                        dict(
                            asset.metadata
                        ),


                    # ------------------------------------------------
                    # Asset history
                    # ------------------------------------------------

                    "history":
                        history_analysis,


                    # ------------------------------------------------
                    # Physical / logical identity
                    # ------------------------------------------------

                    "identity":
                    {
                        "serial":
                            asset.identity.serial,

                        "model":
                            asset.identity.model,

                        "vendor":
                            asset.identity.vendor,

                        "firmware":
                            asset.identity.firmware,

                        "device":
                            asset.identity.device,

                    },


                    # ------------------------------------------------
                    # Observations
                    # ------------------------------------------------

                    "observations":
                    [

                        {
                            "type":
                                obs.type,

                            "value":
                                obs.value,

                            "severity":
                                obs.severity,

                            "source":
                                obs.source,

                            "timestamp":
                                obs.timestamp.isoformat(),

                        }

                        for obs
                        in observations

                    ],


                    # ------------------------------------------------
                    # Topology / dependency intelligence
                    # ------------------------------------------------

                    "relationships":
                        serialized_relationships,

                }

            )



        # ------------------------------------------------------------
        # Deterministic asset summary
        #
        # Keep the full inventory for reasoning, but expose compact
        # aggregate facts so smaller local models do not need to count
        # or infer global inventory information from a large JSON blob.
        # ------------------------------------------------------------

        asset_types = {}
        asset_status = {}
        asset_criticality = {}

        for asset in inventory:

            asset_type = asset.get("type", "UNKNOWN")
            asset_state = asset.get("status", "UNKNOWN")
            asset_level = asset.get("criticality", "UNKNOWN")

            asset_types[asset_type] = (
                asset_types.get(asset_type, 0) + 1
            )

            asset_status[asset_state] = (
                asset_status.get(asset_state, 0) + 1
            )

            asset_criticality[asset_level] = (
                asset_criticality.get(asset_level, 0) + 1
            )

        asset_summary = {
            "count": len(inventory),
            "by_type": dict(sorted(asset_types.items())),
            "by_status": dict(sorted(asset_status.items())),
            "by_criticality": dict(sorted(asset_criticality.items())),
        }


        context = {


            "system":
            {
                "snapshot":
                    snapshot
            },


            # ------------------------------------------------------------
            # Deterministic asset summary
            #
            # Keep the full inventory for detailed reasoning, but expose
            # compact aggregate facts so smaller local models do not need
            # to count or infer global inventory information.
            # ------------------------------------------------------------

            "assets":
            {
                "count":
                    len(inventory),

                "summary":
                    asset_summary,

                "inventory":
                    inventory
            },


            "health":
            {
                "findings":
                    active_findings
            },


            "events":
            {

                "active":
                    active_events,


                "history":
                    self.database.get_events(
                        20
                    ),

            },


            "analytics":
            {

                "summary":
                    self.analytics.summary(),


                "top_events":
                    self.analytics.top_events(
                        5
                    ),


                "categories":
                    self.analytics.by_category(),


                "average_duration":
                    self.analytics.average_duration(),

            },


            "incidents":
                incidents,


            "recommendations":
                recommendations,


            "git":
                self.git.build_context(),


            "logs":
                logs,


            "ai_runtime":
                self.ai_runtime.report()
                if hasattr(self, "ai_runtime")
                else {},

        }



        context["changes"] = (

            self.change_detector.analyze(
                context["git"]
            )

        )



        context["correlations"] = (

            self.intelligence.analyze(
                context
            )

        )



        context["reasoning"] = (

            self.reasoning.analyze(
                context
            )

        )



        return context
