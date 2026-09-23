from atlas.context.builder import ContextBuilder
from atlas.services.intelligence.context.builder import (
    IntelligenceContextBuilder,
)


class OperationalContextBuilder:
    """Canonical ATLAS operational context."""

    SCHEMA_VERSION = "1.0"

    def __init__(self, ai_runtime=None):
        self.infrastructure_builder = ContextBuilder()
        self.intelligence_builder = IntelligenceContextBuilder(
            ai_runtime=ai_runtime
        )

    def build(self):
        infrastructure_context = self._build_infrastructure()
        intelligence_context = self._build_intelligence()

        return self._compose(
            infrastructure_context,
            intelligence_context,
        )

    def build_for_incident(self, incident_id):
        infrastructure_context = self._build_infrastructure()

        intelligence_context = (
            self.intelligence_builder
            .build_for_incident(incident_id)
        )

        return self._compose(
            infrastructure_context,
            intelligence_context.to_dict(),
        )

    def _build_infrastructure(self):
        from atlas.services.infrastructure import (
            InfrastructureService,
        )

        infrastructure = InfrastructureService().collect()

        return self.infrastructure_builder.build(
            infrastructure
        )

    def _build_intelligence(self):
        context = self.intelligence_builder.build()
        return context.to_dict()

    def _compose(
        self,
        infrastructure,
        intelligence,
    ):
        infrastructure = infrastructure or {}
        intelligence = intelligence or {}

        return {
            "schema_version": self.SCHEMA_VERSION,

            "system": (
                infrastructure.get("system")
                or intelligence.get(
                    "infrastructure",
                    {},
                )
            ),

            "infrastructure": intelligence.get(
                "infrastructure",
                infrastructure,
            ),

            "assets": (
                intelligence.get("assets")
                or infrastructure.get(
                    "assets",
                    {},
                )
            ),

            "topology": intelligence.get(
                "topology",
                {},
            ),

            "health": (
                intelligence.get("health")
                or infrastructure.get(
                    "health",
                    {},
                )
            ),

            "events": intelligence.get(
                "events",
                {},
            ),

            "incidents": intelligence.get(
                "incidents",
                [],
            ),

            "lifecycle": intelligence.get(
                "operational_state",
                {},
            ),

            "history": intelligence.get(
                "history",
                [],
            ),

            "knowledge": intelligence.get(
                "knowledge",
            ),

            "learning": intelligence.get(
                "learning",
                [],
            ),

            "changes": intelligence.get(
                "changes",
                {},
            ),

            "recommendations": intelligence.get(
                "recommendations",
                [],
            ),

            "ai_runtime": intelligence.get(
                "ai_runtime",
                {},
            ),

            "actions": intelligence.get(
                "actions",
                [],
            ),

            "sources": {
                "infrastructure_context":
                    infrastructure,

                "intelligence_context":
                    intelligence,
            },
        }
