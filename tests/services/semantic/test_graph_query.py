from atlas.core.asset import (
    Asset,
    AssetType,
)

from atlas.services.assets.registry import (
    AssetRegistry,
)

from atlas.services.semantic.graph_query import (
    SemanticGraphQueryService,
)


class FakeGraph:

    def __init__(
        self,
        relationships,
    ):

        self.relationships = list(
            relationships
        )


    def get_children(
        self,
        asset_id,
    ):

        return [
            relation
            for relation
            in self.relationships
            if relation[
                "source"
            ] == asset_id
        ]


    def get_parents(
        self,
        asset_id,
    ):

        return [
            relation
            for relation
            in self.relationships
            if relation[
                "target"
            ] == asset_id
        ]


def make_asset(
    asset_id,
    name,
    *,
    group=None,
    scope="node-a",
):

    metadata = {}

    if group:

        metadata[
            "semantic_groups"
        ] = [
            {
                "kind":
                    "application_stack",

                "value":
                    group,

                "scope":
                    scope,

                "source":
                    "synthetic_discovery",

                "confidence":
                    1.0,
            }
        ]

    return Asset(
        id=asset_id,
        name=name,
        type=AssetType.APPLICATION,
        metadata=metadata,
    )


def relation(
    source,
    target,
    relation_type,
):

    return {
        "source":
            source,

        "target":
            target,

        "type":
            relation_type,

        "confidence":
            0.99,

        "evidence":
            [
                "synthetic discovery"
            ],
    }


def build_registry():

    registry = AssetRegistry()

    assets = (
        make_asset(
            "nebula-api",
            "api-random",
            group="nebula",
        ),
        make_asset(
            "nebula-db",
            "db-random",
            group="nebula",
        ),
        make_asset(
            "nebula-cache",
            "cache-random",
            group="nebula",
        ),
        make_asset(
            "nebula-worker",
            "worker-random",
            group="nebula",
        ),
        make_asset(
            "external-monitor",
            "monitor-random",
        ),
    )

    for asset in assets:
        registry.register(
            asset
        )

    return registry


def build_graph():

    return FakeGraph(
        [
            relation(
                "nebula-api",
                "nebula-db",
                "DEPENDS_ON",
            ),
            relation(
                "nebula-api",
                "nebula-cache",
                "DEPENDS_ON",
            ),
            relation(
                "external-monitor",
                "nebula-api",
                "MONITORS",
            ),
        ]
    )


def test_group_query_unions_relationships_of_all_members():

    service = SemanticGraphQueryService(
        build_registry(),
        graph=build_graph(),
    )

    result = service.query(
        "nebula",
        relationship="DEPENDS_ON",
        orientation="OUTGOING",
        depth=1,
    )

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert (
        result["entity"]["kind"]
        == "GROUP"
    )

    assert result["count"] == 2

    edges = {
        (
            item[
                "source_asset_id"
            ],
            item[
                "target_asset_id"
            ],
        )
        for item in result[
            "results"
        ]
    }

    assert edges == {
        (
            "nebula-api",
            "nebula-db",
        ),
        (
            "nebula-api",
            "nebula-cache",
        ),
    }


def test_group_query_does_not_choose_a_primary_member():

    service = SemanticGraphQueryService(
        build_registry(),
        graph=build_graph(),
    )

    result = service.query(
        "nebula",
        relationship="DEPENDS_ON",
        orientation="OUTGOING",
        depth=1,
    )

    assert (
        result["entity"][
            "asset_id"
        ]
        is None
    )

    assert set(
        result["entity"][
            "member_ids"
        ]
    ) == {
        "nebula-api",
        "nebula-db",
        "nebula-cache",
        "nebula-worker",
    }


def test_incoming_dependency_query_is_inverse():

    service = SemanticGraphQueryService(
        build_registry(),
        graph=build_graph(),
    )

    result = service.query(
        "db-random",
        relationship="DEPENDS_ON",
        orientation="INCOMING",
        depth=1,
    )

    assert result["count"] == 1

    item = result[
        "results"
    ][0]

    assert (
        item[
            "source_asset_id"
        ]
        == "nebula-api"
    )

    assert (
        item[
            "target_asset_id"
        ]
        == "nebula-db"
    )


def test_relationship_filter_does_not_mix_graph_semantics():

    service = SemanticGraphQueryService(
        build_registry(),
        graph=build_graph(),
    )

    result = service.query(
        "nebula",
        relationship="MONITORS",
        orientation="INCOMING",
        depth=1,
    )

    assert result["count"] == 1

    assert (
        result[
            "results"
        ][0][
            "source_asset_id"
        ]
        == "external-monitor"
    )


def test_unknown_entity_does_not_guess():

    service = SemanticGraphQueryService(
        build_registry(),
        graph=build_graph(),
    )

    result = service.query(
        "unknown-stack",
        relationship="DEPENDS_ON",
        orientation="OUTGOING",
    )

    assert (
        result["status"]
        == "NOT_FOUND"
    )

    assert result["results"] == []


def test_group_query_accepts_canonical_reference():

    service = SemanticGraphQueryService(
        build_registry(),
        graph=build_graph(),
    )

    resolved = (
        service
        .entity_resolver
        .resolve(
            "nebula"
        )
    )

    reference = resolved.reference

    assert reference is not None

    result = service.query(
        reference,
        relationship="DEPENDS_ON",
        orientation="OUTGOING",
        depth=1,
    )

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert (
        result["entity"]["kind"]
        == "GROUP"
    )

    assert (
        result["entity"]["reference"]
        == reference
    )

    edges = {
        (
            item[
                "source_asset_id"
            ],
            item[
                "target_asset_id"
            ],
        )
        for item in result[
            "results"
        ]
    }

    assert edges == {
        (
            "nebula-api",
            "nebula-db",
        ),
        (
            "nebula-api",
            "nebula-cache",
        ),
    }
