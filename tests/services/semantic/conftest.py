import pytest

from atlas.core.asset import (
    Asset,
    AssetType,
)

from atlas.core.relationship import (
    Relationship,
    RelationshipType,
)

from atlas.services.assets.registry import (
    AssetRegistry,
)

from atlas.services.semantic.api import (
    AtlasSemanticAPI,
)

from atlas.services.semantic.query import (
    SemanticQueryEngine,
)

from atlas.storage.asset_repository import (
    AssetRepository,
)

from atlas.storage.graph_repository import (
    GraphRepository,
)


@pytest.fixture
def semantic_runtime():
    """
    Deterministic infrastructure used by semantic tests.

    Names and IDs are intentionally synthetic so tests validate
    ATLAS semantics rather than Bruno's current homelab.
    """

    registry = AssetRegistry()

    node = Asset(
        id="vm-synthetic-node-alpha",
        name="node-alpha",
        type=AssetType.VM,
    )

    runtime = Asset(
        id="service-synthetic-runtime-alpha",
        name="runtime-alpha",
        type=AssetType.SERVICE,
    )

    application = Asset(
        id="application-synthetic-app-alpha",
        name="app-alpha",
        type=AssetType.APPLICATION,
    )

    dependent = Asset(
        id="application-synthetic-dependent-alpha",
        name="dependent-alpha",
        type=AssetType.APPLICATION,
    )

    assets = (
        node,
        runtime,
        application,
        dependent,
    )

    repository = AssetRepository()

    for asset in assets:

        registry.register(
            asset
        )

        repository.save_asset(
            asset
        )


    graph = GraphRepository()

    relationships = (
        Relationship(
            source=node.id,
            target=runtime.id,
            type=RelationshipType.PROVIDES,
            confidence=0.99,
            evidence=[
                "synthetic runtime relationship",
            ],
        ),

        Relationship(
            source=runtime.id,
            target=application.id,
            type=RelationshipType.RUNS,
            confidence=0.99,
            evidence=[
                "synthetic execution relationship",
            ],
        ),

        Relationship(
            source=dependent.id,
            target=node.id,
            type=RelationshipType.DEPENDS_ON,
            confidence=0.99,
            evidence=[
                "synthetic dependency relationship",
            ],
        ),
    )

    for relationship in relationships:

        graph.save_relationship(
            relationship
        )


    api = AtlasSemanticAPI(
        registry=registry
    )

    engine = SemanticQueryEngine(
        api=api
    )

    return {
        "registry":
            registry,

        "api":
            api,

        "engine":
            engine,

        "target":
            node.id,

        "target_name":
            node.name,

        "runtime":
            runtime.id,

        "application":
            application.id,

        "dependent":
            dependent.id,
    }
