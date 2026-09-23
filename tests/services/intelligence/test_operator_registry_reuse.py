from types import SimpleNamespace

from atlas.services.intelligence.context.builder import (
    IntelligenceContextBuilder,
)
from atlas.services.intelligence.operator import (
    IntelligenceOperator,
)
from atlas.services.intelligence.action.proposal import (
    IncidentActionProposalService,
)


class FakeRegistry:

    def __init__(
        self,
        assets=None,
    ):

        self._assets = list(
            assets
            or []
        )

        self.register_calls = 0


    def assets(
        self,
    ):

        return list(
            self._assets
        )


    def register(
        self,
        asset,
    ):

        self.register_calls += 1

        raise AssertionError(
            "supplied registry must not be re-registered"
        )


def test_context_builder_reuses_supplied_registry_without_discovery():

    assets = [
        SimpleNamespace(
            id="asset-1"
        ),
        SimpleNamespace(
            id="asset-2"
        ),
    ]

    registry = FakeRegistry(
        assets
    )

    builder = IntelligenceContextBuilder(
        registry=registry
    )

    assert builder.registry is registry

    assert (
        builder.discovery
        is None
    )

    loaded = (
        builder._load_assets()
    )

    assert loaded == assets

    assert (
        registry.register_calls
        == 0
    )


def test_context_builder_without_registry_keeps_discovery_path():

    builder = (
        IntelligenceContextBuilder()
    )

    assert (
        builder.discovery
        is not None
    )

    assert (
        builder._registry_supplied
        is False
    )


def test_operator_propagates_registry_to_context_builder():

    registry = FakeRegistry()

    operator = IntelligenceOperator(
        registry=registry
    )

    assert (
        operator.context_builder.registry
        is registry
    )

    assert (
        operator.context_builder.discovery
        is None
    )


def test_proposal_service_propagates_registry_to_default_operator():

    registry = FakeRegistry()

    service = IncidentActionProposalService(
        registry=registry
    )

    assert (
        service.operator
        .context_builder
        .registry
        is registry
    )

    assert (
        service.operator
        .context_builder
        .discovery
        is None
    )
