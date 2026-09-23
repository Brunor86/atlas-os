from types import SimpleNamespace

from atlas.services.collector.operational_cycle import (
    OperationalCycleService,
)

from atlas.services.collector.worker import (
    CollectorWorker,
)


class FakeCollector:

    def __init__(
        self,
        calls,
    ):

        self.calls = calls


    def collect(
        self,
    ):

        self.calls.append(
            "collect"
        )

        return {
            "infra":
                "infra",

            "health":
                "health",

            "insights":
                [
                    "insight-1"
                ],

            "logs":
                "logs",
        }


class FakeRegistry:

    def assets(
        self,
    ):

        return []


class FakeDiscovery:

    def __init__(
        self,
        calls,
    ):

        self.calls = calls

        self.registry = (
            FakeRegistry()
        )


    def discover(
        self,
    ):

        self.calls.append(
            "discover"
        )

        return SimpleNamespace(
            assets=[],
            count=0,
        )


class FakeEventService:

    def __init__(
        self,
        calls,
    ):

        self.calls = calls

        self.received = None


    def process(
        self,
        insights,
    ):

        self.calls.append(
            "events.process"
        )

        self.received = (
            insights
        )

        return insights


class FakeEventRepository:

    def __init__(
        self,
        calls,
    ):

        self.calls = calls


    def get_active_events(
        self,
    ):

        self.calls.append(
            "events.active"
        )

        return [
            {
                "title":
                    "Docker"
            }
        ]


class FakeIncidentRecovery:

    def __init__(
        self,
        calls,
    ):

        self.calls = calls
        self.received = []


    def reconcile(
        self,
        incidents,
        *,
        authoritative=True,
    ):

        self.calls.append(
            "incidents.recovery"
        )

        self.received.append(
            {
                "incidents":
                    list(
                        incidents
                    ),

                "authoritative":
                    authoritative,
            }
        )

        return {
            "status":
                "SUCCESS",

            "authoritative":
                authoritative,

            "current_incidents":
                [
                    getattr(
                        incident,
                        "incident_id",
                        None,
                    )
                    for incident
                    in incidents
                ],

            "transitions":
                [],
        }


class FakeAssetReconciler:

    def __init__(
        self,
        calls,
    ):

        self.calls = calls
        self.received = []


    def reconcile(
        self,
        assets,
    ):

        self.calls.append(
            "assets.reconcile"
        )

        self.received.append(
            assets
        )

        return {
            "counts": {
                "ACTIVE": 0,
                "STALE": 0,
                "RETIRED": 0,
            },
            "transitions": [],
        }


class FakeNOC:

    def __init__(
        self,
        calls,
    ):

        self.calls = calls

        self.knowledge_updates = []

        self.contexts = []


    def set_knowledge(
        self,
        knowledge,
        graph,
    ):

        self.calls.append(
            "noc.knowledge"
        )

        self.knowledge_updates.append(
            (
                knowledge,
                graph,
            )
        )


    def generate(
        self,
        context,
    ):

        self.calls.append(
            "noc.generate"
        )

        self.contexts.append(
            context
        )

        return SimpleNamespace(
            status="HEALTHY",
            incidents=[],
        )


class FakeKnowledge:

    def __init__(
        self,
        registry,
        sequence,
    ):

        self.registry = registry
        self.sequence = sequence


class RecordingKnowledgeFactory:

    def __init__(
        self,
    ):

        self.calls = []


    def __call__(
        self,
        registry,
    ):

        result = FakeKnowledge(
            registry,
            len(
                self.calls
            )
            + 1,
        )

        self.calls.append(
            result
        )

        return result


class FakeGraph:

    def __init__(
        self,
        registry,
    ):

        self.registry = registry


class RecordingGraphFactory:

    def __init__(
        self,
    ):

        self.calls = []


    def __call__(
        self,
        registry,
    ):

        result = FakeGraph(
            registry
        )

        self.calls.append(
            result
        )

        return result


def build_cycle():

    calls = []

    collector = FakeCollector(
        calls
    )

    discovery = FakeDiscovery(
        calls
    )

    events = FakeEventService(
        calls
    )

    event_repository = (
        FakeEventRepository(
            calls
        )
    )

    asset_reconciler = (
        FakeAssetReconciler(
            calls
        )
    )

    incident_recovery = (
        FakeIncidentRecovery(
            calls
        )
    )

    noc = FakeNOC(
        calls
    )

    knowledge_factory = (
        RecordingKnowledgeFactory()
    )

    graph_factory = (
        RecordingGraphFactory()
    )

    cycle = OperationalCycleService(
        collector=collector,
        discovery=discovery,
        event_service=events,
        event_repository=event_repository,
        noc=noc,
        knowledge_factory=knowledge_factory,
        graph_factory=graph_factory,
        asset_reconciler=(
            asset_reconciler
        ),
        incident_recovery=(
            incident_recovery
        ),
    )

    return (
        cycle,
        calls,
        events,
        noc,
        knowledge_factory,
        graph_factory,
        asset_reconciler,
    )


def test_operational_cycle_runs_authoritative_pipeline_in_order():

    (
        cycle,
        calls,
        events,
        noc,
        knowledge_factory,
        graph_factory,
        asset_reconciler,
    ) = build_cycle()

    result = (
        cycle.run_once()
    )

    assert calls == [
        "collect",
        "discover",
        "assets.reconcile",
        "events.process",
        "events.active",
        "noc.knowledge",
        "noc.generate",
        "incidents.recovery",
    ]

    assert events.received == [
        "insight-1"
    ]

    assert noc.contexts == [
        {
            "health":
                "health",

            "events":
                [
                    {
                        "title":
                            "Docker"
                    }
                ],
        }
    ]

    assert result[
        "infra"
    ] == "infra"

    assert result[
        "health"
    ] == "health"

    assert result[
        "insights"
    ] == [
        "insight-1"
    ]

    assert result[
        "logs"
    ] == "logs"

    assert result[
        "discovery"
    ].count == 0

    assert result[
        "events"
    ] == [
        {
            "title":
                "Docker"
        }
    ]

    assert result[
        "noc"
    ].status == "HEALTHY"

    assert result[
        "recovery"
    ] == {
        "status":
            "SUCCESS",

        "authoritative":
            True,

        "current_incidents":
            [],

        "transitions":
            [],
    }


def test_operational_cycle_refreshes_knowledge_each_cycle_but_reuses_graph():

    (
        cycle,
        calls,
        events,
        noc,
        knowledge_factory,
        graph_factory,
        asset_reconciler,
    ) = build_cycle()

    cycle.run_once()
    cycle.run_once()

    assert len(
        knowledge_factory.calls
    ) == 2

    assert (
        knowledge_factory.calls[0]
        is not
        knowledge_factory.calls[1]
    )

    assert len(
        graph_factory.calls
    ) == 1

    assert len(
        noc.knowledge_updates
    ) == 2

    first_graph = (
        noc.knowledge_updates[0][1]
    )

    second_graph = (
        noc.knowledge_updates[1][1]
    )

    assert (
        first_graph
        is second_graph
    )


def test_operational_cycle_runs_one_discovery_per_cycle():

    (
        cycle,
        calls,
        events,
        noc,
        knowledge_factory,
        graph_factory,
        asset_reconciler,
    ) = build_cycle()

    cycle.run_once()
    cycle.run_once()

    assert (
        calls.count(
            "discover"
        )
        == 2
    )


class FakeCycle:

    def __init__(
        self,
    ):

        self.calls = 0


    def run_once(
        self,
    ):

        self.calls += 1

        return {
            "infra":
                "infra",

            "health":
                "health",

            "insights":
                [],

            "logs":
                [],
        }


def test_collector_worker_delegates_to_operational_cycle():

    cycle = FakeCycle()

    worker = CollectorWorker(
        interval=300,
        cycle=cycle,
    )

    result = (
        worker.collect_once()
    )

    assert cycle.calls == 1

    assert (
        worker.collector
        is cycle
    )

    assert result[
        "infra"
    ] == "infra"

    assert result[
        "health"
    ] == "health"

    assert (
        "insights"
        in result
    )


class DegradedDiscovery:

    def __init__(
        self,
        calls,
    ):

        self.calls = calls

        self.registry = (
            FakeRegistry()
        )


    def discover(
        self,
    ):

        self.calls.append(
            "discover"
        )

        return SimpleNamespace(
            assets=[],
            count=0,
            complete=False,
            errors=[
                "Proxmox: unavailable",
            ],
        )


def test_operational_cycle_skips_mutating_noc_when_discovery_is_degraded():

    calls = []

    collector = FakeCollector(
        calls
    )

    discovery = DegradedDiscovery(
        calls
    )

    events = FakeEventService(
        calls
    )

    event_repository = (
        FakeEventRepository(
            calls
        )
    )

    asset_reconciler = (
        FakeAssetReconciler(
            calls
        )
    )

    noc = FakeNOC(
        calls
    )

    cycle = OperationalCycleService(
        collector=collector,
        discovery=discovery,
        event_service=events,
        event_repository=event_repository,
        noc=noc,
        knowledge_factory=(
            RecordingKnowledgeFactory()
        ),
        graph_factory=(
            RecordingGraphFactory()
        ),
        asset_reconciler=(
            asset_reconciler
        ),
    )

    result = (
        cycle.run_once()
    )

    assert calls == [
        "collect",
        "discover",
        "events.process",
        "events.active",
    ]

    assert result[
        "discovery"
    ].complete is False

    assert result[
        "noc"
    ] is None

    assert result[
        "recovery"
    ] is None

    assert noc.contexts == []

    assert (
        noc.knowledge_updates
        == []
    )

    assert (
        asset_reconciler.received
        == []
    )


def test_operational_cycle_forwards_persistent_incident_identity_to_recovery():

    (
        cycle,
        calls,
        events,
        noc,
        knowledge_factory,
        graph_factory,
        asset_reconciler,
    ) = build_cycle()

    current = SimpleNamespace(
        incident_id="INC-0042"
    )

    def generate(
        context,
    ):

        calls.append(
            "noc.generate"
        )

        noc.contexts.append(
            context
        )

        return SimpleNamespace(
            status="WARNING",
            incidents=[
                current
            ],
        )

    noc.generate = generate

    result = cycle.run_once()

    recovery = (
        cycle.incident_recovery
    )

    assert (
        recovery.received
        == [
            {
                "incidents":
                    [
                        current
                    ],

                "authoritative":
                    True,
            }
        ]
    )

    assert (
        result["recovery"][
            "current_incidents"
        ]
        == [
            "INC-0042"
        ]
    )


def test_degraded_discovery_never_invokes_incident_recovery():

    calls = []

    recovery = FakeIncidentRecovery(
        calls
    )

    cycle = OperationalCycleService(
        collector=FakeCollector(
            calls
        ),
        discovery=DegradedDiscovery(
            calls
        ),
        event_service=FakeEventService(
            calls
        ),
        event_repository=FakeEventRepository(
            calls
        ),
        noc=FakeNOC(
            calls
        ),
        knowledge_factory=(
            RecordingKnowledgeFactory()
        ),
        graph_factory=(
            RecordingGraphFactory()
        ),
        asset_reconciler=(
            FakeAssetReconciler(
                calls
            )
        ),
        incident_recovery=recovery,
    )

    result = cycle.run_once()

    assert (
        "incidents.recovery"
        not in calls
    )

    assert recovery.received == []

    assert result["recovery"] is None
