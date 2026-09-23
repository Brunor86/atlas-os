from atlas.services.collector.service import (
    CollectorService,
)

from atlas.services.discovery.kernel import (
    DiscoveryKernel,
)

from atlas.services.events.service import (
    EventService,
)

from atlas.storage.event_repository import (
    EventRepository,
)

from atlas.services.noc.service import (
    NOCService,
)

from atlas.services.knowledge.service import (
    KnowledgeService,
)

from atlas.services.knowledge.graph import (
    GraphService,
)

from atlas.services.assets.reconciliation import (
    AssetReconciliationService,
)

from atlas.services.incidents.recovery import (
    IncidentRecoveryService,
)


class OperationalCycleService:
    """
    Authoritative background operational cycle.

    The dashboard is read-only. This service owns the periodic
    mutation path for:

        snapshot collection
        asset discovery / graph persistence
        event reconciliation
        NOC incident synchronization
        action proposal generation

    It does not approve or execute infrastructure actions.
    """

    def __init__(
        self,
        collector=None,
        discovery=None,
        event_service=None,
        event_repository=None,
        noc=None,
        knowledge_factory=None,
        graph_factory=None,
        asset_reconciler=None,
        incident_recovery=None,
    ):

        self.collector = (
            collector
            or CollectorService()
        )

        self.discovery = (
            discovery
            or DiscoveryKernel()
        )

        self.event_service = (
            event_service
            or EventService()
        )

        self.event_repository = (
            event_repository
            or EventRepository()
        )

        #
        # NOC is created lazily after the first authoritative
        # Discovery so its Operator receives the populated
        # registry from the beginning.
        #
        self.noc = noc

        self.knowledge_factory = (
            knowledge_factory
            or KnowledgeService
        )

        self.graph_factory = (
            graph_factory
            or GraphService
        )

        #
        # GraphService can safely be reused because it references
        # the same mutable registry and reads persisted topology.
        #
        # KnowledgeService is intentionally rebuilt each cycle:
        # it caches knowledge cards after first use.
        #
        self.graph = None

        self.asset_reconciler = (
            asset_reconciler
        )

        #
        # Created lazily so read-only/unit consumers that never
        # reach an authoritative NOC cycle do not initialize
        # incident persistence unnecessarily.
        #
        self.incident_recovery = (
            incident_recovery
        )


    def _get_incident_recovery(
        self,
    ):

        if (
            self.incident_recovery
            is None
        ):

            self.incident_recovery = (
                IncidentRecoveryService()
            )

        return (
            self.incident_recovery
        )


    def _get_asset_reconciler(
        self,
    ):

        if (
            self.asset_reconciler
            is None
        ):

            self.asset_reconciler = (
                AssetReconciliationService()
            )

        return (
            self.asset_reconciler
        )


    def _get_noc(
        self,
    ):

        if self.noc is None:

            self.noc = NOCService(
                registry=(
                    self.discovery.registry
                ),
                mutations_enabled=True,
            )

        return self.noc


    def _refresh_knowledge(
        self,
        noc,
    ):

        knowledge = (
            self.knowledge_factory(
                self.discovery.registry
            )
        )

        if self.graph is None:

            self.graph = (
                self.graph_factory(
                    self.discovery.registry
                )
            )

        noc.set_knowledge(
            knowledge,
            self.graph,
        )


    def run_once(
        self,
    ):

        #
        # 1. Existing infrastructure collection path.
        #
        # CollectorService remains the single owner of snapshot
        # collection and persistence.
        #
        collected = (
            self.collector.collect()
        )


        #
        # 2. One authoritative Discovery per operational cycle.
        #
        discovery_result = (
            self.discovery.discover()
        )


        discovery_complete = getattr(
            discovery_result,
            "complete",
            True,
        )

        reconciliation_result = None

        #
        # Inventory reconciliation is allowed only when Discovery
        # explicitly represents a complete authoritative inventory.
        #
        if discovery_complete:

            reconciliation_result = (
                self._get_asset_reconciler()
                .reconcile(
                    discovery_result.assets
                )
            )


        #
        # 3. Reconcile current insights into persisted events.
        #
        self.event_service.process(
            collected[
                "insights"
            ]
        )

        active_events = (
            self.event_repository
            .get_active_events()
        )


        #
        # 4. Mutating NOC.
        #
        # NOC may only mutate persistent incident/action state
        # when Discovery is authoritative.
        #
        # A partial inventory is useful telemetry, but it must
        # never be interpreted as proof that assets disappeared
        # or as sufficient context for operational proposals.
        #
        noc_result = None
        recovery_result = None

        if discovery_complete:

            noc = (
                self._get_noc()
            )

            self._refresh_knowledge(
                noc
            )

            noc_result = (
                noc.generate(
                    {
                        "health":
                            collected[
                                "health"
                            ],

                        "events":
                            active_events,
                    }
                )
            )

            #
            # NOC synchronization must happen first:
            # every currently detected NOCIncident now carries
            # its authoritative persistent INC-xxxx identity.
            #
            # Only a complete Discovery cycle can provide
            # negative evidence strong enough to advance
            # OPEN -> RECOVERING -> RESOLVED.
            #
            recovery_result = (
                self._get_incident_recovery()
                .reconcile(
                    (
                        getattr(
                            noc_result,
                            "incidents",
                            [],
                        )
                        or []
                    ),
                    authoritative=True,
                )
            )


        #
        # Preserve the historical CollectorService result contract
        # while exposing the additional operational products.
        #
        return {
            **collected,

            "discovery":
                discovery_result,

            "reconciliation":
                reconciliation_result,

            "events":
                active_events,

            "noc":
                noc_result,

            "recovery":
                recovery_result,
        }
