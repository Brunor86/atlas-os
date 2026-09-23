from atlas.services.snapshots.loader import SnapshotLoader

from atlas.storage.incident_repository import IncidentRepository
from atlas.storage.event_repository import EventRepository
from atlas.storage.incident_lifecycle_repository import IncidentLifecycleRepository

from atlas.services.discovery.kernel import DiscoveryKernel
from atlas.services.assets.runtime import get_asset_registry

from atlas.services.knowledge.service import KnowledgeService
from atlas.models.intelligence import IntelligenceContext
from atlas.services.intelligence.memory.service import IntelligenceMemoryService



class IntelligenceContextBuilder:


    def __init__(
        self,
        ai_runtime=None,
        registry=None,
    ):

        self.snapshot_loader = SnapshotLoader()

        self.incidents = IncidentRepository()

        self.events = EventRepository()

        self.lifecycle_repository = IncidentLifecycleRepository()

        self._registry_supplied = (
            registry is not None
        )

        self.registry = (
            registry
            if registry is not None
            else get_asset_registry()
        )

        self.discovery = (
            None
            if self._registry_supplied
            else DiscoveryKernel()
        )

        self.knowledge = None

        self.ai_runtime = ai_runtime

        self.memory = IntelligenceMemoryService(
            self.incidents
        )





    def _load_assets(
        self,
    ):
        """
        Reuse an explicitly supplied authoritative registry.

        Standalone intelligence consumers retain historical
        discovery behavior when no registry is supplied.
        """

        if self._registry_supplied:

            return list(
                self.registry.assets()
            )


        assets = (
            self.discovery
            .discover()
            .assets
        )


        #
        # Preserve historical standalone behavior.
        #
        for asset in assets:

            self.registry.register(
                asset
            )


        return assets



    def build(self):

        infrastructure = (
            self.snapshot_loader.load()
        )


        assets = (
            self._load_assets()
        )




        self.knowledge = KnowledgeService(
            self.registry
        )


        incidents = (
            self.incidents.get_all()
        )


        events = (
            self.events.get_recent_events(
                50
            )
        )


        knowledge = self.knowledge


        learning = (
            self.incidents.get_learning_records()
        )

        return IntelligenceContext(

            infrastructure=infrastructure,

            knowledge=knowledge,

            assets=assets,

            incidents=incidents,

            events=events,

            learning=learning,

            history=[],

            actions=[],

        ai_runtime=self.ai_runtime,

        )

    def build_for_incident(
        self,
        incident_id,
    ):
        """
        Build an intelligence context focused on one persistent incident.

        The persistent IncidentManager identifier (INC-xxxx) is the
        authoritative operational identity.
        """

        infrastructure = (
            self.snapshot_loader.load()
        )

        assets = (
            self._load_assets()
        )


        self.knowledge = KnowledgeService(
            self.registry
        )

        incidents = (
            self.incidents.get_all()
        )

        incident = None

        for candidate in incidents:
            candidate_id = None

            if isinstance(candidate, dict):
                candidate_id = (
                    candidate.get("id")
                    or candidate.get("incident_id")
                )

            elif hasattr(candidate, "id"):
                candidate_id = getattr(
                    candidate,
                    "incident_id",
                    None,
                ) or getattr(
                    candidate,
                    "id",
                    None,
                )

            elif isinstance(candidate, (tuple, list)):
                if candidate:
                    candidate_id = candidate[0]

            if candidate_id == incident_id:
                incident = candidate
                break

        if incident is None:
            raise ValueError(
                f"Incident not found: {incident_id}"
            )

        events = (
            self.events.get_recent_events(
                50
            )
        )

        incident_events = []

        for event in events:
            event_incident_id = None

            if isinstance(event, dict):
                event_incident_id = (
                    event.get("incident_id")
                )

            elif hasattr(event, "incident_id"):
                event_incident_id = getattr(
                    event,
                    "incident_id",
                    None,
                )

            elif isinstance(event, (tuple, list)):
                if event:
                    event_incident_id = event[0]

            if event_incident_id == incident_id:
                incident_events.append(event)

        learning = (
            self.incidents.get_learning_records()
        )

        lifecycle = (
            self.lifecycle_repository.get_by_incident(
                incident_id
            )
        )

        enriched_lifecycle = []

        previous_timestamp = None
        previous_state = None

        from datetime import datetime, timezone

        for sequence, record in enumerate(
            lifecycle,
            start=1,
        ):
            enriched = dict(record)

            enriched["sequence"] = sequence
            enriched["previous_state"] = previous_state

            duration_seconds = 0

            timestamp = enriched.get(
                "timestamp"
            )

            if (
                previous_timestamp is not None
                and timestamp
            ):
                try:
                    current_dt = datetime.fromisoformat(
                        timestamp
                    )

                    duration_seconds = (
                        current_dt
                        - previous_timestamp
                    ).total_seconds()

                except (
                    ValueError,
                    TypeError,
                ):
                    duration_seconds = 0

            enriched["duration_seconds"] = (
                duration_seconds
            )

            enriched_lifecycle.append(
                enriched
            )

            if timestamp:
                try:
                    previous_timestamp = (
                        datetime.fromisoformat(
                            timestamp
                        )
                    )
                except (
                    ValueError,
                    TypeError,
                ):
                    previous_timestamp = None

            previous_state = enriched.get(
                "state"
            )

        # Build a compact operational state from lifecycle history.
        current_state = None
        previous_operational_state = None
        last_actor = None
        last_transition_at = None
        last_transition_duration = 0

        if enriched_lifecycle:
            latest = enriched_lifecycle[-1]

            current_state = latest.get("state")

            previous_operational_state = latest.get("previous_state")

            last_actor = latest.get("actor")

            last_transition_at = latest.get("timestamp")

            last_transition_duration = latest.get(
            "duration_seconds",
            0,
        )

        operational_state = {
            "current_state": current_state,
            "previous_state": previous_operational_state,
            "lifecycle_events": len(enriched_lifecycle),
            "last_actor": last_actor,
            "last_transition_at": last_transition_at,
            "last_transition_duration_seconds": last_transition_duration,
            "is_terminal": current_state == "RESOLVED",
            "has_transition": (
            previous_operational_state is not None
            and current_state is not None
            and previous_operational_state != current_state
            ),
        }

        return IntelligenceContext(
            infrastructure=infrastructure,
            knowledge=self.knowledge,
            assets=assets,
            incidents=[incident],
            events=incident_events,
            learning=learning,
            history=enriched_lifecycle,
            operational_state=operational_state,
            actions=[],

        ai_runtime=self.ai_runtime,
        )
