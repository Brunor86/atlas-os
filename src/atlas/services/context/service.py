from datetime import datetime, UTC

from atlas.models.event import Event

from atlas.storage.repository import SnapshotRepository
from atlas.storage.incident_repository import IncidentRepository

from atlas.services.health.service import HealthService
from atlas.services.insights.service import InsightService
from atlas.services.knowledge.service import KnowledgeService
from atlas.services.intelligence.reasoning.service import IntelligenceReasoner
from atlas.services.noc.impact import ImpactEngine
from atlas.services.intelligence.safety.service import ActionSafetyService
from atlas.services.intelligence.recommendation.service import ActionRecommendationService
from atlas.services.intelligence.action.builder import SafeActionBuilder
from atlas.services.intelligence.memory.service import IntelligenceMemoryService
from atlas.services.intelligence.learning.service import IncidentLearningService

from atlas.services.snapshots.loader import SnapshotLoader
from atlas.services.intelligence.context.builder import IntelligenceContextBuilder


class ContextService:


    def __init__(self):

        self.repository = SnapshotRepository()

        self.incident_repository = IncidentRepository()

        self.loader = SnapshotLoader()

        self.context_builder = IntelligenceContextBuilder()

        self.health = HealthService()

        self.insights = InsightService()

        self.reasoning_engine = IntelligenceReasoner()

        self.impact = ImpactEngine()

        from atlas.services.assets.runtime import (
            get_asset_registry,
        )

        self.knowledge = KnowledgeService(
            get_asset_registry()
        )

        self.safety = ActionSafetyService()

        self.recommendation = ActionRecommendationService()

        self.action_builder = SafeActionBuilder()

        self.memory = IntelligenceMemoryService(
            self.incident_repository
        )

        self.learning = IncidentLearningService(
            self.incident_repository
        )



    def _dependency_impact(self, asset_id):
        """
        Compatibility projection for intelligence consumers.

        Canonical impact traversal is provided by ImpactEngine /
        TopologyTraversalService. This preserves the historical
        dependency-impact contract for intelligence consumers.
        """

        if not asset_id:
            return {
                "asset": asset_id,
                "upstream": [],
                "downstream": [],
                "affected": [],
                "severity": "UNKNOWN",
            }

        result = self.impact.analyze(
            asset_id
        )

        if not result or "error" in result:
            return {
                "asset": asset_id,
                "upstream": [],
                "downstream": [],
                "affected": [],
                "severity": "UNKNOWN",
            }

        upstream = result.get(
            "operational_upstream",
            result.get(
                "upstream",
                [],
            ),
        )

        downstream = result.get(
            "downstream",
            [],
        )

        upstream = [
            item.get("asset_id")
            if isinstance(item, dict)
            else item
            for item in upstream
        ]

        downstream = [
            item.get("asset_id")
            if isinstance(item, dict)
            else item
            for item in downstream
        ]

        affected = list(
            dict.fromkeys(
                upstream + downstream
            )
        )

        return {
            "asset": asset_id,
            "upstream": upstream,
            "downstream": downstream,
            "affected": affected,
            "severity": result.get(
                "severity",
                "UNKNOWN",
            ),
        }


    def _events_from_health(
        self,
        health,
        assets=None,
    ):
        """
        Project structured Health alerts into Events.

        Health rules own detection and affected-resource identity.
        ContextService must not rediscover the failed resource.
        """

        events = []

        if not health:
            return events

        now = datetime.now(
            UTC
        ).isoformat()

        assets_by_id = {
            str(
                getattr(
                    asset,
                    "id",
                    "",
                )
            ):
                asset

            for asset in (
                assets
                or []
            )

            if getattr(
                asset,
                "id",
                None,
            )
        }

        for alert in (
            getattr(
                health,
                "alerts",
                [],
            )
            or []
        ):

            affected_assets = list(
                getattr(
                    alert,
                    "affected_assets",
                    [],
                )
                or []
            )

            #
            # Structured path:
            # one Event for each exact affected asset.
            #
            if affected_assets:

                for asset_id in affected_assets:

                    asset_id = str(
                        asset_id
                    )

                    asset = assets_by_id.get(
                        asset_id
                    )

                    metadata = (
                        getattr(
                            asset,
                            "metadata",
                            {},
                        )
                        or {}
                    )

                    data = {
                        "source":
                            alert.source,
                    }

                    if (
                        alert.source
                        == "docker"
                    ):

                        data.update(
                            {
                                "container":
                                    metadata.get(
                                        "container_name",
                                        getattr(
                                            asset,
                                            "name",
                                            asset_id,
                                        ),
                                    ),

                                "image":
                                    metadata.get(
                                        "image"
                                    ),

                                "status":
                                    metadata.get(
                                        "docker_status"
                                    ),
                            }
                        )

                    events.append(
                        Event(
                            type=
                                "HEALTH_ALERT",

                            title=
                                alert.title,

                            message=
                                alert.message,

                            first_seen=
                                now,

                            last_seen=
                                now,

                            status=
                                "active",

                            severity=
                                alert.severity,

                            asset_id=
                                asset_id,

                            data=
                                data,
                        )
                    )

                continue

            #
            # Compatibility path for health rules that do not
            # yet expose affected_assets.
            #
            events.append(
                Event(
                    type=
                        "HEALTH_ALERT",

                    title=
                        alert.title,

                    message=
                        alert.message,

                    first_seen=
                        now,

                    last_seen=
                        now,

                    status=
                        "active",

                    severity=
                        alert.severity,

                    asset_id=
                        alert.source,

                    data={
                        "source":
                            alert.source,
                    },
                )
            )

        return events


    def build(self):

        context = self.context_builder.build()

        if context is None:

            return None


        infra = context.infrastructure


        knowledge = None

        if infra:

            self.knowledge._ensure_loaded()

            knowledge = self.knowledge


        health = None

        if infra or context.assets:

            health = self.health.evaluate(
                infra,
                context.assets,
            )


        events = self._events_from_health(
            health,
            context.assets,
        )


        insights = []

        if health:

            insights = self.insights.generate(
                infra,
                health,
                context.assets,
            )


        dependency_impact = (
            self._dependency_impact(
                "docker"
            )
        )


        health_context = {

            "health": "unknown",

            "alerts": [],

        }


        if health:

            health_context = {

                "health": health.status,

                "alerts": [

                    {

                        "source": a.source,

                        "title": a.title,

                        "message": a.message,

                        "severity": a.severity,

                    }

                    for a in health.alerts

                ],

            }


        reasoning = self.reasoning_engine.reason(

            [

                {

                    "title": i.title,

                    "message": i.summary,

                    "severity": i.severity,

                }

                for i in insights

            ],

            health_context,

            dependency_impact,

        )


        memory = (
            self.memory.lookup(
                "docker",
                "container stopped",
            )
        )


        recommendation = (
            self.recommendation.recommend_from_reasoning(
                reasoning,
                incident_id="",
                memory=memory,
            )
        )



        safe_action = (
            self.action_builder.build(
                recommendation
            )
        )



        dependency_impact = None

        if (
            recommendation is not None
            and recommendation.action
            and knowledge
        ):

            dependency_impact = (
                self._dependency_impact(
                    "docker"
                )
            )




        latest = self.repository.get_latest()

        history = self.repository.get_history(
            50
        )


        return {

            "snapshot": latest,

            "history": history,
            "knowledge": knowledge,

            "memory": memory,

            "health": health,

            "events": events,

            "insights": insights,

            "intelligence": {

                "reasoning": reasoning,

                "recommendation": recommendation,

                "safe_action": safe_action,

                "dependency_impact": dependency_impact,

            },

            "infrastructure": infra,

        }
