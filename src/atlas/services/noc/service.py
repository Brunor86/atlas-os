import logging
import hashlib
import json

from atlas.models.noc import (
    NOCStatus,
    NOCIssue,
    NOCIncident,
)

from atlas.models.event import Event
from atlas.models.incident import Incident
from atlas.models.incident_intelligence import IncidentIntelligence


from atlas.services.noc.rules.health_rule import HealthRule
from atlas.services.noc.rules.event_rule import EventRule
from atlas.services.noc.correlation import NOCCorrelation
from atlas.services.noc.intelligence import NOCIntelligence
from atlas.services.intelligence.explanation.service import NOCExplanationService
from atlas.services.noc.root_cause import RootCauseEngine
from atlas.services.noc.severity import SeverityEngine
from atlas.services.noc.severity_intelligence import SeverityIntelligence
from atlas.services.noc.impact import ImpactEngine
from atlas.services.noc.impact_serializer import ImpactSerializer
from atlas.services.intelligence.history.memory import IncidentMemory
from atlas.services.intelligence.memory.intelligence import IncidentMemoryIntelligence
from atlas.services.intelligence.learning.service import IncidentLearningService
from atlas.services.intelligence.recommendation.service import ActionRecommendationService
from atlas.services.intelligence.decision.service import IntelligenceDecisionService
from atlas.services.intelligence.approval.service import ActionApprovalService
from atlas.services.intelligence.approval.policy import ActionApprovalPolicy
from atlas.services.intelligence.safety.service import ActionSafetyService
from atlas.services.intelligence.executor.service import ActionExecutorService
from atlas.services.intelligence.remediation.service import RemediationService
from atlas.services.intelligence.action.proposal import (
    IncidentActionProposalService,
)
from atlas.storage.action_repository import ActionRepository
from atlas.storage.incident_lifecycle_repository import IncidentLifecycleRepository

from atlas.services.incidents.manager import IncidentManager
from atlas.services.incidents.lifecycle import IncidentLifecycle
from atlas.services.knowledge.service import KnowledgeService
from atlas.services.knowledge.graph import GraphService
from atlas.services.assets.runtime import get_asset_registry
from atlas.services.context.service import ContextService
from atlas.services.ai.service import AIService



logger = logging.getLogger(__name__)


def _diagnostic(*parts):

    message = " ".join(
        str(part)
        for part in parts
    )

    if "ERROR" in message.upper():

        logger.warning(
            "%s",
            message,
        )

    else:

        logger.debug(
            "%s",
            message,
        )


def normalize_events(events):

    normalized = []


    for event in events or []:


        if isinstance(event, dict):

            normalized.append(

                Event(

                    type=event.get(
                        "type",
                        "unknown",
                    ),

                    title=event.get(
                        "title",
                        "unknown",
                    ),

                    message=event.get(
                        "message",
                        "",
                    ),

                    first_seen=event.get(
                        "first_seen",
                        "",
                    ),

                    last_seen=event.get(
                        "last_seen",
                        "",
                    ),

                    status=event.get(
                        "status",
                        "unknown",
                    ),

                    severity=event.get(
                        "severity",
                        "warning",
                    ),

                    asset_id=event.get(
                        "asset_id"
                    ),

                )

            )


        else:

            normalized.append(
                event
            )


    return normalized





class NOCService:


    def __init__(
        self,
        registry=None,
        *,
        mutations_enabled=True,
    ):


        self.context_service = ContextService()

        self.mutations_enabled = bool(
            mutations_enabled
        )


        self.rules = [

            HealthRule(),

            EventRule(),

        ]


        self.correlation = NOCCorrelation()


        self.intelligence = NOCIntelligence()

        self.ai = AIService()

        self.explanation = NOCExplanationService()


        self.severity = SeverityEngine()


        self.severity_intelligence = SeverityIntelligence()

        self.impact = ImpactEngine()

        self.impact_serializer = ImpactSerializer()

        self.registry = registry or get_asset_registry()

        self.knowledge = None

        self.graph = None

        self.root_cause = None


        self.incident_manager = IncidentManager()


        self.lifecycle = IncidentLifecycle(
            IncidentLifecycleRepository()
        )


        self.history_memory = IncidentMemory(
            self.incident_manager.repository
        )


        self.memory_intelligence = IncidentMemoryIntelligence(
            self.incident_manager.repository
        )


        self.learning = IncidentLearningService(
            self.incident_manager.repository
        )


        self.recommendation = ActionRecommendationService(
            self.incident_manager.repository
        )


        self.decision = IntelligenceDecisionService()


        self.action_repository = ActionRepository(
            self.incident_manager.repository.database
        )

        self.action_proposals = (
            IncidentActionProposalService(
                action_repository=(
                    self.action_repository
                ),
                incident_repository=(
                    self.incident_manager.repository
                ),
                registry=(
                    self.registry
                ),
            )
        )


        self.approval = ActionApprovalService(
            self.action_repository
        )


        self.approval_policy = ActionApprovalPolicy()


        self.safety = ActionSafetyService()


        self.executor = ActionExecutorService(
            self.action_repository,
            self.incident_manager.repository,
        )


        self.remediation = RemediationService()






    def _sync_incident(
        self,
        incident,
    ):
        """
        Synchronize persistent incident state only when mutations
        are enabled.

        Read-only consumers may resolve an existing persistent
        incident identity, but never create or update one.
        """

        if self.mutations_enabled:

            return (
                self.incident_manager
                .sync_incident(
                    incident
                )
            )

        existing = (
            self.incident_manager
            .find_open(
                incident
            )
        )

        if not existing:
            return None

        persistent_id = existing[0]

        incident.incident_id = (
            persistent_id
        )

        return persistent_id


    _LIFECYCLE_VOLATILE_KEYS = {
        "id",
        "incident_id",
        "timestamp",
        "created_at",
        "updated_at",
        "generated_at",
        "first_seen",
        "last_seen",
    }


    @classmethod
    def _normalize_lifecycle_value(
        cls,
        value,
    ):

        if value is None:

            return None

        if isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        ):

            return value

        if hasattr(
            value,
            "to_dict",
        ):

            try:

                return (
                    cls
                    ._normalize_lifecycle_value(
                        value.to_dict()
                    )
                )

            except Exception:

                pass

        if hasattr(
            value,
            "__dataclass_fields__",
        ):

            try:

                from dataclasses import asdict

                return (
                    cls
                    ._normalize_lifecycle_value(
                        asdict(value)
                    )
                )

            except Exception:

                pass

        if isinstance(
            value,
            dict,
        ):

            return {
                str(key):
                    cls._normalize_lifecycle_value(
                        item
                    )

                for key, item
                in sorted(
                    value.items(),
                    key=lambda pair:
                        str(pair[0]),
                )

                if str(key)
                not in (
                    cls
                    ._LIFECYCLE_VOLATILE_KEYS
                )
            }

        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):

            normalized = [
                cls._normalize_lifecycle_value(
                    item
                )
                for item in value
            ]

            return sorted(
                normalized,
                key=lambda item:
                    json.dumps(
                        item,
                        sort_keys=True,
                        default=str,
                    ),
            )

        if hasattr(
            value,
            "__dict__",
        ):

            return (
                cls
                ._normalize_lifecycle_value(
                    vars(value)
                )
            )

        return str(value)


    @staticmethod
    def _incident_value(
        incident,
        key,
        default=None,
    ):

        if isinstance(
            incident,
            dict,
        ):

            return incident.get(
                key,
                default,
            )

        return getattr(
            incident,
            key,
            default,
        )


    @classmethod
    def _lifecycle_fingerprint(
        cls,
        incident,
        state,
    ):

        keys = (
            "name",
            "title",
            "asset",
            "severity",
            "events",
            "impact",
            "root_cause",
            "diagnosis",
            "blast_radius",
            "suggested_actions",
            "recommendation",
            "decision",
            "safe_action",
        )

        payload = {
            "state":
                str(
                    state
                    or ""
                ),

            "incident":
                {
                    key:
                        cls._normalize_lifecycle_value(
                            cls._incident_value(
                                incident,
                                key,
                            )
                        )

                    for key
                    in keys
                },
        }

        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
            default=str,
        )

        return hashlib.sha256(
            encoded.encode(
                "utf-8"
            )
        ).hexdigest()


    def _transition_incident(
        self,
        incident,
        state,
        detail="",
    ):
        """
        Keep lifecycle reasoning in memory while suppressing
        persistence for read-only consumers.
        """

        fingerprint = None

        if self.mutations_enabled:

            fingerprint = (
                self._lifecycle_fingerprint(
                    incident,
                    state,
                )
            )


        return self.lifecycle.transition(
            incident,
            state,
            detail,
            persist=self.mutations_enabled,
            fingerprint=fingerprint,
        )


    def _propose_incident_action(
        self,
        incident,
    ):
        """
        Generate or reuse an operator proposal for a
        persistent incident.

        NOC is proposal-only:
        this method never approves or executes an action.
        """

        incident_id = str(
            getattr(
                incident,
                "incident_id",
                "",
            )
            or ""
        ).strip()

        if not incident_id:

            result = {
                "status":
                    "NO_PROPOSAL",

                "reason":
                    "persistent incident id is missing",

                "execution_allowed":
                    False,
            }

        else:

            try:

                proposal = (
                    self.action_proposals
                    .propose(
                        incident_id
                    )
                )

                result = dict(
                    proposal
                    or {}
                )

                result[
                    "execution_allowed"
                ] = False

            except Exception as exc:

                result = {
                    "status":
                        "ERROR",

                    "incident_id":
                        incident_id,

                    "reason":
                        str(exc),

                    "execution_allowed":
                        False,
                }

                _diagnostic(
                    "DEBUG NOC ACTION PROPOSAL ERROR:",
                    exc,
                )

        incident.action_proposal = (
            result
        )

        #
        # Keep the historical approval_context field useful
        # to existing UI/serialization consumers, but it now
        # represents proposal state only.
        #
        incident.approval_context = (
            result
        )

        return result


    def set_knowledge(
        self,
        knowledge,
        graph=None,
    ):

        self.knowledge = knowledge

        self.graph = graph

        if self.root_cause is None:

            self.root_cause = RootCauseEngine(
                self.knowledge,
                self.graph,
            )

        else:

            self.root_cause.knowledge = knowledge

            self.root_cause.graph = graph


    def prepare_context(
        self,
        context,
    ):

        if context is None:

            context = {}

        context["events"] = normalize_events(
            context.get(
                "events",
                []
            )
        )

        return context



    def load_knowledge(self):

        _diagnostic("DEBUG LOAD KNOWLEDGE START")

        if self.knowledge is None:

            _diagnostic("DEBUG CREATE KnowledgeService")

            self.knowledge = KnowledgeService(
                self.registry
            )

            _diagnostic("DEBUG KnowledgeService OK")

            _diagnostic("DEBUG CREATE GraphService")

            self.graph = GraphService(self.registry)

            _diagnostic("DEBUG GraphService OK")

            _diagnostic("DEBUG CREATE RootCauseEngine")

            self.root_cause = RootCauseEngine(
                self.knowledge,
                self.graph,
            )

            _diagnostic("DEBUG RootCauseEngine OK")

        return self.knowledge



    def generate(
        self,
        context=None,
    ):

        if context is None:

            context = self.context_service.build()


        context = self.prepare_context(
            context
        )


        signals = []



        for rule in self.rules:



            if isinstance(
                rule,
                HealthRule
            ):


                signals.extend(

                    rule.evaluate(

                        context.get(
                            "health"
                        )

                    )

                )


            elif isinstance(
                rule,
                EventRule
            ):


                signals.extend(

                    rule.evaluate(

                        context.get(
                            "events"
                        )

                    )

                )





        score = sum(

            signal.get(
                "impact",
                0
            )

            for signal in signals

        )






        priority = "LOW"



        if score >= 70:

            priority = "HIGH"


        elif score >= 30:

            priority = "MEDIUM"





        status = "HEALTHY"



        if score >= 70:

            status = "CRITICAL"


        elif score >= 30:

            status = "WARNING"





        issues = []



        for signal in signals:


            issues.append(

                NOCIssue(

                    service=signal.get(
                        "source",
                        "unknown",
                    ),


                    issue_type=signal.get(
                        "severity",
                        "unknown",
                    ),


                    severity=signal.get(
                        "severity",
                        "unknown",
                    ),


                    description=signal.get(
                        "message",
                        "",
                    ),

                )

            )





        health = context.get(
            "health",
            {}
        )


        logs = context.get(
            "logs",
            []
        )


        
        _diagnostic(
            "DEBUG EVENTS BEFORE CORRELATION:",
            context.get("events", [])
        )

        raw_incidents = self.correlation.analyze(

            context.get(
                "events",
                []
            )

        )



        _diagnostic(
            "DEBUG RAW INCIDENTS RESULT:",
            raw_incidents
        )



        incidents = []



        for incident in raw_incidents:

            incident["reasoning_timeline"] = [
                {
                    "stage": "event",
                    "title": "Infrastructure event detected",
                    "data": {
                        "event": (
                            incident.get("events", [{}])[0].get(
                                "title",
                                "unknown",
                            )
                            if incident.get("events")
                            else "unknown"
                        ),
                        "asset": (
                            incident.get("events", [{}])[0].get(
                                "asset_id",
                                "unknown",
                            )
                            if incident.get("events")
                            else "unknown"
                        ),
                    },
                }
            ]

            severity_context = (
                self.severity_intelligence.analyze(
                    NOCIncident(
                        name=incident.get(
                            "name",
                            "unknown",
                        ),
                        confidence=incident.get(
                            "confidence",
                            0,
                        ),
                        reason=incident.get(
                            "reason",
                            "",
                        ),
                        severity=incident.get(
                            "severity",
                            "UNKNOWN",
                        ),
                        asset=incident.get(
                            "asset",
                        ) or "unknown",
                        impact=incident.get(
                            "impact",
                            [],
                        ),
                    )
                )
            )

            incident["severity"] = (
                severity_context.get(
                    "severity",
                    "UNKNOWN",
                )
            )

            incident["incident_score"] = (
                severity_context.get(
                    "score",
                    0,
                )
            )

            incident["severity_context"] = severity_context

            #
            incident.setdefault(
                "reasoning_timeline",
                []
            )

            incident["reasoning_timeline"].append(
                {
                    "stage": "severity",
                    "title": "Severity calculated",
                    "data": {
                        "severity": severity_context.get(
                            "severity",
                            "UNKNOWN",
                        ),
                        "score": severity_context.get(
                            "score",
                            0,
                        ),
                    },
                }
            )


            #
            # Impact Intelligence
            #

            _diagnostic("DEBUG BEFORE IMPACT INCIDENT:", incident)

            asset_id = incident.get(
                "asset"
            )

            _diagnostic("DEBUG IMPACT ORIGINAL ASSET:", asset_id)
            _diagnostic(
                "DEBUG IMPACT AFFECTED:",
                incident.get("affected_assets")
            )


            if asset_id:

                try:

                    impact_result = self.impact.analyze(
                        asset_id
                    )

                    incident["impact_intelligence"] = (
                        self.impact_serializer.serialize(
                            impact_result
                        )
                    )

                except Exception as e:

                    _diagnostic(
                        "IMPACT ERROR:",
                        e
                    )

                    incident["impact_intelligence"] = {}

            else:

                incident["impact_intelligence"] = {}

            # Normalize impact intelligence into incident impact
            if not incident.get("impact"):
                impact_intelligence = incident.get(
                    "impact_intelligence",
                    {}
                )

                affected = (
                    impact_intelligence.get("affected_assets", [])
                    if isinstance(impact_intelligence, dict)
                    else []
                )

                incident["impact"] = affected

            _diagnostic(
                "DEBUG FINAL IMPACT BEFORE NOCIncident:",
                incident.get("impact")
            )

            incidents.append(
                NOCIncident(
                    name=incident.get(
                        "name",
                        "unknown",
                    ),
                    confidence=incident.get(
                        "confidence",
                        0,
                    ),
                    severity=incident.get(
                        "severity",
                        "UNKNOWN",
                    ),

                    impact_intelligence=incident.get(
                        "impact_intelligence",
                        {},
                    ),
                    incident_score=incident.get(
                        "incident_score",
                        0,
                    ),
                    reason=incident.get(
                        "reason",
                        "",
                    ),
                    asset=(
                        incident.get(
                            "asset",
                        )
                        or next(
                            (
                                e.get(
                                    "asset_id"
                                )
                                for e in incident.get(
                                    "events",
                                    []
                                )
                                if e.get(
                                    "asset_id"
                                )
                            ),
                            "unknown",
                        )
                    ),

                    affected_assets=(
                        incident.get(
                            "affected_assets",
                        )
                        or [
                            e.get(
                                "asset_id"
                            )
                            for e in incident.get(
                                "events",
                                []
                            )
                            if e.get(
                                "asset_id"
                            )
                        ]
                    ),
                    events=incident.get(
                        "events",
                        [],
                    ),
                    impact=incident.get(
                        "impact",
                        [],
                    ),

                    root_cause=incident.get(
                        "root_cause",
                        "",
                    ),
                    diagnosis=incident.get(
                        "diagnosis",
                        "",
                    ),
                    blast_radius=incident.get(
                        "blast_radius",
                        [],
                    ),
                    suggested_actions=incident.get(
                        "suggested_actions",
                        [],
                    ),
                    evidence=incident.get(
                        "evidence",
                        [],
                    ),
                    severity_context=incident.get(
                        "severity_context",
                        {},
                    ),
                    reasoning_timeline=incident.get(
                        "reasoning_timeline",
                        [],
                    ),
                    intelligence=IncidentIntelligence(
                        recommendation=incident.get(
                            "recommendation",
                            {},
                        ),
                        memory=incident.get(
                            "memory",
                            {},
                        ),
                        memory_intelligence=incident.get(
                            "memory_intelligence",
                            {},
                        ),
                        decision=incident.get(
                            "decision",
                            {},
                        ),
                        safe_action=incident.get(
                            "safe_action",
                            {},
                        ),
                        approval_policy=incident.get(
                            "approval_policy",
                            {},
                        ),
                        approval_context=incident.get(
                            "approval_context",
                            {},
                        ),
                        execution_context=incident.get(
                            "execution_context",
                            {},
                        ),
                        remediation_context=incident.get(
                            "remediation_context",
                            {},
                        ),
                        learning_context=incident.get(
                            "learning_context",
                            {},
                        ),
                        reasoning_timeline=incident.get(
                            "reasoning_timeline",
                            [],
                        ),
                        lifecycle=incident.get(
                            "lifecycle",
                            [],
                        ),
                    ),
                )
            )

        for incident in incidents:

            #
            # Persist incident identity BEFORE lifecycle reasoning.
            #
            # The lifecycle engine must always use the persistent
            # INC-xxxx identifier, never the internal NOCIncident UUID.
            #
            persistent_id = self._sync_incident(
                incident
            )

            # Persistent operational identity must be available
            # before any lifecycle transition.
            incident.incident_id = persistent_id

            try:


                  asset_id = None

                  # Buscar asset desde eventos
                  if incident.events:

                      event = incident.events[0]

                      if isinstance(event, dict):

                          asset_id = event.get(
                              "asset_id"
                          )

                  # Fallback: buscar asset en evidencia
                  if not asset_id:

                      for evidence in getattr(
                          incident,
                          "evidence",
                          []
                      ):

                          if isinstance(evidence, dict):

                              asset_id = evidence.get(
                                  "asset_id"
                              )

                              if asset_id:
                                  break


                  if asset_id and self.knowledge:

                      application = self.knowledge.resolve_application(
                          asset_id
                      )

                      results = self.knowledge.impact(
                          application
                      )

                      incident.impact = [
                          {
                              "asset_id": result.asset_id,
                              "application": result.application,
                              "importance": result.importance,
                              "roles": result.roles,
                              "depth": result.depth,
                              "reason": result.reason,
                          }
                          for result in results
                      ]

                  else:

                      incident.impact = []


            except Exception as exc:


                incident.impact = []





            #
            # Root Cause Analysis
            #

            try:
                _diagnostic(
                    "DEBUG ROOT KNOWLEDGE BEFORE ANALYZE:",
                    type(self.root_cause.knowledge),
                )

                _diagnostic("DEBUG FORCE KNOWLEDGE LOAD")

                self.root_cause.knowledge._ensure_loaded()

                _diagnostic(
                    "DEBUG KNOWLEDGE CARDS:",
                    len(self.root_cause.knowledge.cards),
                )

                _diagnostic("=== DEBUG ROOT EVENTS ===")
                _diagnostic(
                    "ROOT EVENTS TYPE:",
                    type(incident.events),
                )
                _diagnostic(
                    "ROOT EVENTS COUNT:",
                    len(incident.events),
                )

                for debug_i, debug_event in enumerate(incident.events):
                    _diagnostic(
                        "ROOT EVENT",
                        debug_i,
                        "TYPE:",
                        type(debug_event),
                        "REPR:",
                        repr(debug_event),
                    )

                    _diagnostic(
                        "  TITLE:",
                        repr(getattr(debug_event, "title", "<NO TITLE>")),
                        "TYPE:",
                        type(getattr(debug_event, "title", None)),
                    )

                    _diagnostic(
                        "  MESSAGE:",
                        repr(getattr(debug_event, "message", "<NO MESSAGE>")),
                        "TYPE:",
                        type(getattr(debug_event, "message", None)),
                    )

                    if isinstance(debug_event, dict):
                        _diagnostic(
                            "  DICT TITLE:",
                            repr(debug_event.get("title")),
                            "TYPE:",
                            type(debug_event.get("title")),
                        )

                        _diagnostic(
                            "  DICT MESSAGE:",
                            repr(debug_event.get("message")),
                            "TYPE:",
                            type(debug_event.get("message")),
                        )

                root_results = self.root_cause.analyze(
                    events=incident.events,
                    logs=logs,
                    health=health,
                    assets=self.registry.assets(),
                )
                if root_results:
                    _diagnostic(
                        "DEBUG ROOT RESULTS:",
                        root_results,
                    )

                    cause = root_results[0]

                    _diagnostic(
                        "DEBUG ROOT CAUSE SELECTED:",
                        cause,
                    )

                    incident.asset = cause.get(
                        "asset",
                        incident.asset,
                    )

                    if not incident.asset:
                        event_assets = [
                            e.get("asset_id")
                            for e in cause.get(
                                "events",
                                [],
                            )
                            if e.get("asset_id")
                        ]

                        if event_assets:
                            incident.asset = event_assets[0]
                            incident.affected_assets = event_assets

                    incident.affected_assets = cause.get(
                        "affected_assets",
                        incident.affected_assets,
                    )

                    incident.blast_radius = cause.get(
                        "blast_radius",
                        incident.blast_radius,
                    )

                    incident.supporting_infrastructure = cause.get(
                        "supporting_infrastructure",
                        incident.supporting_infrastructure,
                    )

                    # Synchronize topology-derived blast radius
                    # with incident impact consumed by downstream intelligence.
                    if incident.blast_radius:
                        incident.impact = [
                            item
                            for item in incident.blast_radius
                            if isinstance(item, dict)
                        ]

                        _diagnostic(
                            "DEBUG IMPACT SYNC:",
                            len(incident.impact),
                            "items from blast_radius",
                        )

                    else:
                        incident.impact = []


                    incident.root_cause = cause.get(
                        "root_cause",
                        cause.get(
                            "name",
                            "",
                        ),
                    )

                    incident.diagnosis = cause.get(
                        "diagnosis",
                        cause.get(
                            "reason",
                            "",
                        ),
                    )

                    #
                    #
                    #
                    # Impact Intelligence after Root Cause
                    #

                    try:

                        if (
                            incident.asset
                            and incident.asset != "unknown"
                        ):

                            impact_result = (
                                self.impact.analyze(
                                    incident.asset
                                )
                            )

                            incident.impact_intelligence = (
                                self.impact_serializer.serialize(
                                    impact_result
                                )
                            )

                        elif incident.affected_assets:

                            impact_result = (
                                self.impact.analyze(
                                    incident.affected_assets[0]
                                )
                            )

                            incident.impact_intelligence = (
                                self.impact_serializer.serialize(
                                    impact_result
                                )
                            )

                        else:

                            incident.impact_intelligence = {}


                    except Exception as exc:

                        _diagnostic(
                            "DEBUG IMPACT ERROR:",
                            exc,
                        )

                        incident.impact_intelligence = {}


                    #
                    # Synchronize operational impact
                    # from Impact Intelligence.
                    #

                    impact_intelligence = (
                        incident.impact_intelligence
                        if isinstance(
                            incident.impact_intelligence,
                            dict,
                        )
                        else {}
                    )

                    # Keep enriched operational impact generated
                    # by topology/root-cause intelligence.
                    if incident.blast_radius:
                        incident.impact = [
                            item
                            for item in incident.blast_radius
                            if isinstance(item, dict)
                        ]

                    _diagnostic(
                        "DEBUG IMPACT SYNC:",
                        len(
                            incident.impact
                        ),
                        "assets from topology impact",
                    )


                    incident.reasoning_timeline.append(
                        {
                            "stage": "root_cause",
                            "title": "Root cause analyzed",
                            "data": {
                                "cause": incident.root_cause,
                                "diagnosis": incident.diagnosis,
                                "asset": incident.asset,
                            },
                        }
                    )

                    history = self.history_memory.recall_history(
                        incident
                    )

                    incident.reasoning_timeline.append(
                        {
                            "stage": "memory",
                            "title": "Historical incidents recalled",
                            "data": {
                                "similar_cases": len(history),
                                "asset": incident.asset,
                            },
                            "confidence": min(
                                len(history) * 0.2,
                                1.0,
                            ),
                        }
                    )

                    self._transition_incident(
                        incident,
                        "DIAGNOSED",
                        "Root cause identified by RCA engine",
                    )

                    incident.memory_intelligence = (
                        self.memory_intelligence.analyze(
                            incident
                        )
                    )

                    incident.reasoning_timeline.append(
                        {
                            "stage": "memory_intelligence",
                            "title": "Historical intelligence analyzed",
                            "data": {
                                "similar_cases": incident.memory_intelligence.get(
                                    "similar_cases",
                                    0,
                                ),
                                "successful_actions": incident.memory_intelligence.get(
                                    "successful_actions",
                                    [],
                                ),
                                "success_rate": incident.memory_intelligence.get(
                                    "success_rate",
                                    0,
                                ),
                            },
                            "confidence": incident.memory_intelligence.get(
                                "confidence",
                                0,
                            ),
                        }
                    )

                    incident.blast_radius = cause.get(
                        "blast_radius",
                        incident.blast_radius,
                    )

                    incident.supporting_infrastructure = cause.get(
                        "supporting_infrastructure",
                        incident.supporting_infrastructure,
                    )

                    incident.severity = self.severity.calculate(
                        incident
                    )

                    incident.severity_context = (
                        self.severity_intelligence.analyze(
                            incident
                        )
                    )

                    incident.learning_context = (
                        self.learning.get_context(
                            incident
                        )
                    )


                    #
                    # Learning confidence boost
                    #

                    learning = incident.learning_context


                    if learning:

                        similar_cases = learning.get(
                            "similar_cases",
                            0
                        )


                        success_rate = learning.get(
                            "success_rate",
                            0
                        )


                        if (
                            similar_cases > 0
                            and
                            success_rate >= 0.8
                        ):

                            incident.confidence = min(
                                1.0,
                                incident.confidence + 0.4
                            )



                    incident.recommendation = (
                        self.recommendation.recommend(
                            incident
                        )
                    )




                    #
                    # AI Incident Reasoning
                    #
                    # AI interpreta la evidencia determinística
                    # ya calculada por ATLAS.
                    #
                    # No reemplaza la recomendación operacional.
                    #

                    try:

                        ai_reasoning = (
                            self.ai.analyze_incident_reasoning(
                                incident
                            )
                        )


                        incident.ai_analysis = dict(
                            ai_reasoning
                        )

                        #
                        # Experimental AI confidence.
                        #
                        # Keep the model confidence separate from
                        # deterministic NOC confidence.
                        #

                        incident.ai_confidence = float(
                            ai_reasoning.get(
                                "confidence",
                                0.0,
                            )
                            or 0.0
                        )

                        _diagnostic(
                            "AI EXPERIMENTAL:",
                            incident.incident_id,
                            "confidence=",
                            incident.ai_confidence,
                            "root_cause=",
                            ai_reasoning.get(
                                "root_cause",
                                "",
                            ),
                        )

                        incident.ai_reasoning = [

                            {
                                "type": "root_cause",

                                "content":
                                    ai_reasoning.get(
                                        "root_cause",
                                        "",
                                    ),
                            },

                            *[
                                {
                                    "type": "evidence",

                                    "content": item,
                                }

                                for item in ai_reasoning.get(
                                    "evidence",
                                    [],
                                )
                            ],

                            *[
                                {
                                    "type": "impact",

                                    "content": item,
                                }

                                for item in ai_reasoning.get(
                                    "impact",
                                    [],
                                )
                            ],
                        ]


                        incident.ai_recommendation = (
                            ai_reasoning.get(
                                "recommendation",
                                "",
                            )
                        )


                        incident.ai_confidence = float(
                            ai_reasoning.get(
                                "confidence",
                                0.0,
                            )
                        )


                        incident.reasoning_timeline.append(
                            {
                                "stage":
                                    "ai_incident_reasoning",

                                "title":
                                    "AI incident reasoning analyzed",

                                "data":
                                    {
                                        "summary":
                                            ai_reasoning.get(
                                                "summary",
                                                "",
                                            ),

                                        "root_cause":
                                            ai_reasoning.get(
                                                "root_cause",
                                                "",
                                            ),

                                        "risk":
                                            ai_reasoning.get(
                                                "risk",
                                                "UNKNOWN",
                                            ),

                                        "recommendation":
                                            ai_reasoning.get(
                                                "recommendation",
                                                "",
                                            ),

                                        "missing_evidence":
                                            ai_reasoning.get(
                                                "missing_evidence",
                                                [],
                                            ),
                                    },

                                "confidence":
                                    incident.ai_confidence,
                            }
                        )


                    except Exception as exc:

                        _diagnostic(
                            "DEBUG AI INCIDENT REASONING ERROR:",
                            exc,
                        )

                        incident.ai_analysis = {}

                        incident.ai_reasoning = []

                        incident.ai_recommendation = ""

                        incident.ai_confidence = 0.0


                incident.decision = (
                    self.decision.build(
                        recommendation=incident.recommendation,
                        memory=incident.memory_intelligence,
                    )
                )


                self._transition_incident(
                    incident,
                    "RECOMMENDED",
                    "Operational recommendation generated",
                )




                incident.safe_action = (
                    self.safety.evaluate(
                        incident
                    )
                )

                #
                # Safety is a hard gate.
                # A blocked action must never reach
                # approval or execution.
                #
                if (
                    incident.safe_action.get(
                        "status"
                    )
                    == "BLOCKED"
                ):

                    self._transition_incident(
                        incident,
                        "BLOCKED",
                        (
                            "Action blocked by safety gate: "
                            + str(
                                incident.safe_action.get(
                                    "reason",
                                    "safety policy rejected action",
                                )
                            )
                        ),
                    )

                    incident.approval_context = {
                        **incident.safe_action,
                        "status": "BLOCKED",
                    }

                    _diagnostic(
                        "SAFETY BLOCK:",
                        incident.safe_action.get(
                            "reason"
                        ),
                    )

                    incident.execution_context = {}
                    incident.remediation_context = {}


                #
                # NOC proposal-only boundary.
                #
                # The legacy pipeline used to auto-approve,
                # execute infrastructure actions, or create
                # approval requests directly from generate().
                #
                # v0.121 moves ownership of persistent action
                # proposals to IncidentActionProposalService.
                #
                incident.approval_policy = {
                    "decision":
                        "PROPOSAL_ONLY",

                    "reason": [
                        (
                            "NOC cannot approve or execute "
                            "infrastructure actions autonomously"
                        )
                    ],
                }

                incident.approval_context = {
                    "status":
                        incident.safe_action.get(
                            "status",
                            "NO_ACTION",
                        ),

                    "incident_id":
                        getattr(
                            incident,
                            "incident_id",
                            "",
                        ),

                    "action":
                        incident.safe_action.get(
                            "action",
                            "",
                        ),

                    "target":
                        incident.safe_action.get(
                            "target",
                            "",
                        ),

                    "risk":
                        incident.safe_action.get(
                            "risk",
                            "UNKNOWN",
                        ),

                    "approval_mode":
                        "HUMAN",

                    "execution_allowed":
                        False,

                    "source":
                        "noc-proposal-only",
                }

                incident.execution_context = {}
                incident.remediation_context = {}


                incident.memory_intelligence = (
                    self.memory_intelligence.analyze(
                        incident
                    )
                )


                if isinstance(
                    incident,
                    dict
                ):

                    incident["severity_context"] = (
                        self.severity_intelligence.analyze(
                            incident
                        )
                    )


                incident.evidence = cause.get(
                    "evidence",
                    [],
                )


                recommendation = cause.get(
                    "recommendation",
                    "",
                )


                if cause.get(
                    "suggested_actions"
                ):

                    incident.suggested_actions = cause.get(
                        "suggested_actions",
                        []
                    )


                elif recommendation:

                    incident.suggested_actions = [
                        recommendation
                    ]


            except Exception:

                pass




            persistent_id = self._sync_incident(
                incident
            )

            # Keep the authoritative persistent incident identity.
            if persistent_id:
                incident.incident_id = persistent_id

                #
                # Incident intelligence may propose an action,
                # but NOC never approves or executes it.
                #
                if self.mutations_enabled:
                    self._propose_incident_action(
                        incident
                    )


            existing = self.incident_manager.find_open(
                incident.name
            )


            if existing:

                incident.incident_id = existing[0]





        #
        # Dependency impact scoring
        #

        for incident in incidents:

            impact = getattr(
                incident,
                "impact",
                []
            )


            for item in impact:

                if not isinstance(
                    item,
                    dict
                ):
                    continue


                if item.get(
                    "importance"
                ) == "HIGH":

                    score += 15




        intelligence = self.intelligence.analyze(

            issues,

            incidents,

        )


        #
        # Incident impact scoring
        #

        for incident in incidents:


            if incident.name == "service_degradation":

                score += 30


            impact = getattr(
                incident,
                "impact",
                []
            )


            if impact:

                score += len(
                    impact
                ) * 10



        #
        # Recalculate priority after impact
        #

        if score >= 70:

            priority = "HIGH"


        elif score >= 30:

            priority = "MEDIUM"


        else:

            priority = "LOW"



        if score >= 70:

            status = "CRITICAL"


        elif score >= 30:

            status = "WARNING"


        else:

            status = "HEALTHY"









        operator_explanations = []


        for incident in incidents:


            explanation = self.explanation.explain(

                incident,


                reasoning={

                    "root_cause":
                        getattr(
                            incident,
                            "root_cause",
                            ""
                        )

                },


                recommendation=getattr(

                    incident,

                    "recommendation",

                    {}

                ),


                learning=getattr(

                    incident,

                    "learning_context",

                    {}

                ),

            )


            operator_explanations.append(

                explanation

            )



        return NOCStatus(

            status=status,


            score=score,


            priority=priority,


            summary=(

                f"NOC analysis completed "
                f"with score {score}"

            ),



            active_events=len(

                context.get(
                    "events",
                    []
                )

            ),



            issues=issues,


            incidents=incidents,


            explanations=intelligence.get(

                "explanations",

                []

            ),



            recommendations=intelligence.get(

                "recommendations",

                []

            ),


            operator_explanation=operator_explanations,

        )
