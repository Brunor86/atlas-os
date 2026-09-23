from types import SimpleNamespace

from atlas.services.incidents.lifecycle import (
    IncidentLifecycle,
)
from atlas.services.noc.service import (
    NOCService,
)


class RecordingLifecycleRepository:

    def __init__(self):
        self.saved = []

    def save(
        self,
        event,
    ):
        self.saved.append(
            event
        )


class RecordingIncidentManager:

    def __init__(
        self,
        existing=None,
    ):
        self.existing = existing
        self.sync_calls = 0
        self.find_calls = 0

    def sync_incident(
        self,
        incident,
    ):
        self.sync_calls += 1

        return "INC-MUTATED"

    def find_open(
        self,
        incident,
    ):
        self.find_calls += 1

        return self.existing


def test_lifecycle_transition_can_be_memory_only():

    repository = (
        RecordingLifecycleRepository()
    )

    lifecycle = IncidentLifecycle(
        repository
    )

    incident = SimpleNamespace(
        id="internal-id",
        incident_id="INC-0001",
        lifecycle=[],
    )

    result = lifecycle.transition(
        incident,
        "DIAGNOSED",
        "read-only dashboard",
        persist=False,
    )

    assert len(result) == 1
    assert (
        result[0]["state"]
        == "DIAGNOSED"
    )

    assert repository.saved == []


def test_noc_read_only_sync_resolves_existing_without_write():

    noc = object.__new__(
        NOCService
    )

    noc.mutations_enabled = False

    noc.incident_manager = (
        RecordingIncidentManager(
            existing=(
                "INC-0042",
                "service_degradation",
            )
        )
    )

    incident = SimpleNamespace(
        name="service_degradation",
        asset="unknown",
        incident_id=None,
    )

    persistent_id = (
        noc._sync_incident(
            incident
        )
    )

    assert persistent_id == "INC-0042"
    assert incident.incident_id == "INC-0042"

    assert (
        noc.incident_manager.sync_calls
        == 0
    )

    assert (
        noc.incident_manager.find_calls
        == 1
    )


def test_noc_read_only_sync_does_not_create_missing_incident():

    noc = object.__new__(
        NOCService
    )

    noc.mutations_enabled = False

    noc.incident_manager = (
        RecordingIncidentManager(
            existing=None
        )
    )

    incident = SimpleNamespace(
        name="new_incident",
        asset="unknown",
        incident_id=None,
    )

    persistent_id = (
        noc._sync_incident(
            incident
        )
    )

    assert persistent_id is None

    assert (
        noc.incident_manager.sync_calls
        == 0
    )


def test_noc_mutation_mode_preserves_existing_sync_behavior():

    noc = object.__new__(
        NOCService
    )

    noc.mutations_enabled = True

    noc.incident_manager = (
        RecordingIncidentManager()
    )

    incident = SimpleNamespace(
        name="service_degradation",
        asset="unknown",
        incident_id=None,
    )

    persistent_id = (
        noc._sync_incident(
            incident
        )
    )

    assert persistent_id == "INC-MUTATED"

    assert (
        noc.incident_manager.sync_calls
        == 1
    )

    assert (
        noc.incident_manager.find_calls
        == 0
    )


def test_noc_read_only_transition_is_memory_only():

    repository = (
        RecordingLifecycleRepository()
    )

    noc = object.__new__(
        NOCService
    )

    noc.mutations_enabled = False

    noc.lifecycle = IncidentLifecycle(
        repository
    )

    incident = SimpleNamespace(
        id="internal-id",
        incident_id="INC-0001",
        lifecycle=[],
    )

    result = noc._transition_incident(
        incident,
        "RECOMMENDED",
        "generated for display",
    )

    assert len(result) == 1
    assert repository.saved == []
