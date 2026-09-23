import pytest


@pytest.fixture(
    autouse=True,
)
def isolated_atlas_database(
    tmp_path,
    monkeypatch,
):
    """
    Every pytest test runs against its own SQLite database.

    Tests must never read or mutate the production atlas.db.

    Runtime registry state is reset as well because it is a
    process-global cache backed by persisted assets.
    """

    database_path = (
        tmp_path
        / "atlas-test.db"
    )

    monkeypatch.setenv(
        "ATLAS_DB_PATH",
        str(database_path),
    )

    from atlas.services.assets import (
        runtime as asset_runtime,
    )

    asset_runtime._registry = None

    yield database_path

    asset_runtime._registry = None


@pytest.fixture
def mcp_synthetic_runtime():
    """
    Deterministic ATLAS knowledge universe for MCP tests.

    The MCP stack itself is real:
        MCPKnowledgeClient
            -> MCP server
            -> Semantic API
            -> AssetRegistry / persisted graph

    Only the infrastructure being queried is synthetic.

    Topology:

        node-alpha [VM]
             |
          PROVIDES
             v
        runtime-alpha
             |
            RUNS
             v
          app-alpha
           /     \
    DEPENDS_ON  DEPENDS_ON
       /           \
 database-alpha   cache-alpha

    A generic SERVER with the same name and a SERVICE referencing
    node-alpha through metadata exercise identity ranking without
    depending on a real host.
    """

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

    from atlas.services.assets import (
        runtime as asset_runtime,
    )

    from atlas.storage.asset_repository import (
        AssetRepository,
    )

    from atlas.storage.graph_repository import (
        GraphRepository,
    )


    registry = AssetRegistry()


    generic_node = Asset(
        id="server-synthetic-node-alpha",
        name="node-alpha",
        type=AssetType.SERVER,
    )


    vm_node = Asset(
        id="vm-synthetic-node-alpha",
        name="node-alpha",
        type=AssetType.VM,
    )


    runtime = Asset(
        id="service-synthetic-runtime-alpha",
        name="runtime-alpha",
        type=AssetType.SERVICE,
    )


    reference_service = Asset(
        id="service-synthetic-reference-alpha",
        name="reference-alpha",
        type=AssetType.SERVICE,
        metadata={
            "hostname":
                "node-alpha",
        },
    )


    group = {
        "kind":
            "application_stack",

        "value":
            "suite-alpha",

        "scope":
            "node-alpha",

        "source":
            "synthetic_provider",

        "confidence":
            1.0,
    }


    application = Asset(
        id="application-synthetic-app-alpha",
        name="app-alpha",
        type=AssetType.APPLICATION,
        metadata={
            # Provider-native metadata used by the current MCP
            # ranking implementation.
            "compose_project":
                "suite-alpha",

            "compose_service":
                "app-alpha",

            # Technology-neutral semantic representation.
            "semantic_groups": [
                group,
            ],
        },
    )


    database = Asset(
        id="application-synthetic-database-alpha",
        name="database-alpha",
        type=AssetType.APPLICATION,
        metadata={
            "compose_project":
                "suite-alpha",

            "compose_service":
                "database-alpha",

            "semantic_groups": [
                group,
            ],
        },
    )


    cache = Asset(
        id="application-synthetic-cache-alpha",
        name="cache-alpha",
        type=AssetType.APPLICATION,
        metadata={
            "compose_project":
                "suite-alpha",

            "compose_service":
                "cache-alpha",

            "semantic_groups": [
                group,
            ],
        },
    )


    assets = (
        generic_node,
        vm_node,
        runtime,
        reference_service,
        application,
        database,
        cache,
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
            source=vm_node.id,
            target=runtime.id,
            type=RelationshipType.PROVIDES,
            confidence=1.0,
            evidence=[
                "synthetic provider relationship",
            ],
        ),

        Relationship(
            source=runtime.id,
            target=application.id,
            type=RelationshipType.RUNS,
            confidence=1.0,
            evidence=[
                "synthetic runtime relationship",
            ],
        ),

        Relationship(
            source=application.id,
            target=database.id,
            type=RelationshipType.DEPENDS_ON,
            confidence=1.0,
            evidence=[
                "synthetic application dependency",
            ],
        ),

        Relationship(
            source=application.id,
            target=cache.id,
            type=RelationshipType.DEPENDS_ON,
            confidence=1.0,
            evidence=[
                "synthetic application dependency",
            ],
        ),
    )


    for relationship in relationships:

        graph.save_relationship(
            relationship
        )


    # MCP server instances created during this test use the same
    # deterministic runtime registry.
    asset_runtime._registry = registry


    return {
        "registry":
            registry,

        "node":
            vm_node.id,

        "application":
            application.id,

        "database":
            database.id,

        "cache":
            cache.id,

        "group":
            "suite-alpha",
    }
