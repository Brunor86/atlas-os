from atlas.core.asset import (
    Asset,
    AssetType,
    ServiceImportance,
)

from atlas.services.assets.registry import (
    AssetRegistry,
)

from atlas.services.assets.topology_traversal import (
    TopologyTraversalService,
)


def make_topology_with_registry(
    registry,
):

    topology = object.__new__(
        TopologyTraversalService
    )

    topology.registry = registry
    topology.assets = None

    return topology


def test_system_service_is_detected_from_domain_model():

    registry = AssetRegistry()

    service = Asset(
        id="arbitrary-node-42",
        name="arbitrary-service",
        type=AssetType.SERVICE,
        service_importance=(
            ServiceImportance.SYSTEM
        ),
    )

    registry.register(
        service
    )

    topology = (
        make_topology_with_registry(
            registry
        )
    )

    assert topology._is_system_service(
        "arbitrary-node-42"
    )


def test_non_system_service_is_not_filtered():

    registry = AssetRegistry()

    service = Asset(
        id="another-arbitrary-node",
        name="business-service",
        type=AssetType.SERVICE,
        service_importance=(
            ServiceImportance.NORMAL
        ),
    )

    registry.register(
        service
    )

    topology = (
        make_topology_with_registry(
            registry
        )
    )

    assert not topology._is_system_service(
        "another-arbitrary-node"
    )


def test_unknown_graph_node_is_not_guessed_from_id():

    registry = AssetRegistry()

    topology = (
        make_topology_with_registry(
            registry
        )
    )

    assert not topology._is_system_service(
        "service-linux-systemd_service-something"
    )
