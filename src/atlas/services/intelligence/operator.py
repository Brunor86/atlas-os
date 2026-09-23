from atlas.models.intelligence import IntelligenceResult

from atlas.storage.repository import SnapshotRepository
from atlas.storage.asset_repository import AssetRepository

from atlas.services.intelligence.context.builder import (
    IntelligenceContextBuilder,
)
from atlas.services.intelligence.analyzer import (
    IntelligenceAnalyzer,
)
from atlas.services.intelligence.reasoning.service import (
    IntelligenceReasoner,
)
from atlas.services.noc.impact import (
    ImpactEngine,
)
from atlas.services.intelligence.recommendation.service import (
    ActionRecommendationService,
)
from atlas.services.intelligence.decision.service import (
    IntelligenceDecisionService,
)
from atlas.services.intelligence.explanation.service import (
    NOCExplanationService,
)
from atlas.services.intelligence.memory.service import (
    IntelligenceMemoryService,
)
from atlas.services.intelligence.safety.service import (
    ActionSafetyService,
)
from atlas.services.intelligence.approval.service import (
    ApprovalService,
)

from atlas.services.intelligence.operator_tools import (
    build_operator_tool_registry,
)


class IntelligenceOperator:

    def __init__(
        self,
        repository=None,
        asset_repository=None,
        registry=None,
    ):

        self.repository = repository

        self.asset_repository = (
            asset_repository
            or AssetRepository()
        )

        self.context_builder = (
            IntelligenceContextBuilder(
                registry=registry
            )
        )

        self.analyzer = IntelligenceAnalyzer()

        self.snapshot_repository = SnapshotRepository()

        self.reasoner = IntelligenceReasoner()

        self.impact = ImpactEngine()

        self.memory = IntelligenceMemoryService(
            repository
        )

        self.recommendation = (
            ActionRecommendationService(
                repository,
                asset_repository=(
                    self.asset_repository
                ),
            )
        )

        self.decision = IntelligenceDecisionService()

        self.explanation = NOCExplanationService()

        self.safety = ActionSafetyService()

        self.approval = ApprovalService()

        self.tools = build_operator_tool_registry(
            asset_repository=(
                self.asset_repository
            ),
        )


    def _dependency_impact(self, asset_id):
        """
        Compatibility projection for the historical dependency
        contract.

        Canonical impact analysis is provided by ImpactEngine and
        TopologyTraversalService.
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
            [],
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
    def execute_tool(
        self,
        name,
        **kwargs,
    ):
        return self.tools.execute(
            name,
            **kwargs,
        )


    def get_tool_context(self):
        return self.tools.describe()


    def inspect_asset(
        self,
        asset_id,
    ):
        return self.tools.execute(
            "inspect_asset",
            asset_id=asset_id,
        )


    def find_asset(
        self,
        query,
    ):
        return self.tools.execute(
            "find_asset",
            query=query,
        )


    def list_assets(
        self,
    ):
        return self.tools.execute(
            "list_assets",
        )


    def analyze(
        self,
        incident_id,
    ):

        context = (
            self.context_builder
            .build_for_incident(
                incident_id
            )
        )

        context_dict = context.to_dict()

        incident = (
            context.incidents[0]
            if context.incidents
            else None
        )

        if incident is None:
            raise ValueError(
                f"Incident not found: {incident_id}"
            )


        current_incident_id = (
            self._get_incident_id(
                incident
            )
        )


        # -------------------------------------------------
        # 1. Deterministic intelligence
        # -------------------------------------------------

        # Analyzer history comes from infrastructure snapshots.
        # Incident lifecycle history is kept separately in context.history.

        metrics_history = (
            self.snapshot_repository.get_history(
                limit=20
            )
        )

        latest_snapshot = (
            self.snapshot_repository.get_latest()
        )

        snapshot_data = (
            latest_snapshot.get(
                "data"
            )
            if latest_snapshot
            else None
        )

        insights = self.analyzer.analyze(
            metrics_history,
            snapshot=snapshot_data,
        )


        # -------------------------------------------------
        # 2. Dependency impact
        # -------------------------------------------------

        dependency = None

        asset_id = self._get_incident_asset(
            incident
        )

        asset_context = None

        if asset_id:

            tool_result = self.execute_tool(
                "get_asset_context",
                asset_id=asset_id,
            )

            if tool_result.status == "SUCCESS":

                asset_context = (
                    tool_result.result
                )

            dependency = (
                self._dependency_impact(
                    asset_id
                )
            )


        # -------------------------------------------------
        # 3. Historical memory
        # -------------------------------------------------

        memory = None

        if asset_id:

            issue = self._get_incident_issue(
                incident
            )

            memory = self.memory.lookup(
                asset_id,
                issue,
            )


        # -------------------------------------------------
        # 4. Reasoning
        # -------------------------------------------------

        reasoning = self.reasoner.reason(
            insights,
            context_dict,
            dependency=dependency,
            asset_context=asset_context,
        )


        # -------------------------------------------------
        # 5. Recommendation
        # -------------------------------------------------

        recommendation = (
            self.recommendation
            .recommend_from_reasoning(
                reasoning,
                memory=memory,
                incident_id=current_incident_id,
            )
        )

        #
        # recommend_from_reasoning() intentionally returns
        # None when the reasoner has no operational action.
        #
        # Keep that public contract unchanged while using a
        # mapping-compatible view internally.
        #
        recommendation_view = (
            recommendation
            or {}
        )


        # -------------------------------------------------
        # 6. Decision
        # -------------------------------------------------

        decision = self.decision.build(
            reasoning=reasoning,
            recommendation=recommendation,
            memory=memory,
        )


        # -------------------------------------------------
        # 7. Explanation
        # -------------------------------------------------

        explanation = self.explanation.explain(
            incident,
            reasoning=reasoning,
            recommendation=recommendation,
            learning=memory,
        )


        # -------------------------------------------------
        # 8. Safety gate
        #
        # IMPORTANT:
        # safety is evaluated against a temporary
        # recommendation object instead of mutating
        # the persistent incident model.
        # -------------------------------------------------

        safety_incident = self._build_safety_incident(
            incident,
            recommendation_view,
            diagnosis=decision.get(
                "diagnosis",
                {},
            ),
        )

        safety = self.safety.evaluate(
            safety_incident
        )


        # -------------------------------------------------
        # 9. Unified result
        # -------------------------------------------------

        result = IntelligenceResult(
            state=decision.get(
                "state",
                reasoning.get(
                    "state",
                    "UNKNOWN",
                ),
            ),
            diagnoses=decision.get(
                "diagnoses",
                reasoning.get(
                    "diagnoses",
                    [],
                ),
            ),

            # Backward compatibility with consumers
            # that still expect a singular diagnosis.
            diagnosis=decision.get(
                "diagnosis",
                reasoning.get(
                    "diagnosis",
                    {},
                ),
            ),
            reasoning=[
                *reasoning.get(
                    "reasoning",
                    []
                ),
                *explanation.get(
                    "explanation",
                    []
                ),
            ],
            risks=reasoning.get(
                "risks",
                []
            ),
            recommended_actions=(
                [
                    {
                        "action":
                            recommendation_view.get(
                                "action"
                            ),

                        "incident_id":
                            (
                                recommendation_view.get(
                                    "incident_id"
                                )
                                or current_incident_id
                            ),

                        "confidence":
                            recommendation_view.get(
                                "confidence",
                                0,
                            ),

                        "risk":
                            recommendation_view.get(
                                "risk",
                                "UNKNOWN",
                            ),

                        "safety":
                            safety,
                    }
                ]
                if recommendation_view.get(
                    "action"
                )
                else []
            ),
        )


        return {
            "incident": incident,
            "context": context_dict,
            "insights": insights,
            "dependency": dependency,
            "asset_context": asset_context,
            "memory": memory,
            "reasoning": reasoning,
            "recommendation": recommendation,
            "decision": decision,
            "explanation": explanation,
            "safety": safety,
            "result": result.to_dict(),
        }


    @staticmethod
    def _get_incident_id(
        incident,
    ):

        if isinstance(
            incident,
            tuple,
        ):

            if incident:
                return incident[0]

            return None


        if isinstance(
            incident,
            dict,
        ):

            return (
                incident.get("incident_id")
                or incident.get("id")
            )


        return (
            getattr(
                incident,
                "incident_id",
                None,
            )
            or getattr(
                incident,
                "id",
                None,
            )
        )


    @staticmethod
    def _get_incident_asset(
        incident,
    ):

        # IncidentRepository currently returns incident rows
        # as tuples. Schema:
        # 0 = incident_id
        # 1 = incident_type
        # 2 = asset_id
        # 3 = severity
        # 4 = status
        #
        # Keep compatibility with dict/object incidents too.

        if isinstance(
            incident,
            tuple,
        ):

            if len(incident) > 2:
                return incident[2]

            return None


        if isinstance(
            incident,
            dict,
        ):

            return (
                incident.get("asset")
                or incident.get("asset_id")
            )


        return (
            getattr(
                incident,
                "asset",
                None,
            )
            or getattr(
                incident,
                "asset_id",
                None,
            )
        )


    @staticmethod
    def _get_incident_issue(
        incident,
    ):

        if isinstance(
            incident,
            dict,
        ):

            return (
                incident.get("root_cause")
                or incident.get("reason")
                or incident.get("name")
                or "unknown issue"
            )


        return (
            getattr(
                incident,
                "root_cause",
                None,
            )
            or getattr(
                incident,
                "reason",
                None,
            )
            or getattr(
                incident,
                "name",
                None,
            )
            or "unknown issue"
        )


    @staticmethod
    def _build_safety_incident(
        incident,
        recommendation,
        diagnosis=None,
    ):

        class SafetyIncident:
            pass

        safety_incident = SafetyIncident()

        safety_incident.asset = (
            IntelligenceOperator
            ._get_incident_asset(
                incident
            )
        )

        safety_incident.recommendation = (
            recommendation or {}
        )

        safety_incident.diagnosis = (
            diagnosis or {}
        )

        safety_incident.incident_id = (
            (recommendation or {}).get(
                "incident_id"
            )
            or IntelligenceOperator
            ._get_incident_id(
                incident
            )
            or ""
        )

        return safety_incident

