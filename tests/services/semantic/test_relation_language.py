from types import SimpleNamespace

from atlas.core.asset import (
    Asset,
    AssetType,
)

from atlas.services.assets.registry import (
    AssetRegistry,
)

from atlas.services.semantic.entity_resolver import (
    SemanticEntityResolver,
)

from atlas.services.semantic.graph_query import (
    SemanticGraphQueryService,
)

from atlas.services.semantic.query import (
    SemanticQueryEngine,
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
            item
            for item
            in self.relationships
            if item["source"]
            == asset_id
        ]


    def get_parents(
        self,
        asset_id,
    ):

        return [
            item
            for item
            in self.relationships
            if item["target"]
            == asset_id
        ]


def make_asset(
    asset_id,
    name,
    *,
    group=None,
):

    metadata = {}

    if group is not None:

        metadata[
            "semantic_groups"
        ] = [
            {
                "kind":
                    "application_stack",

                "value":
                    group,

                "scope":
                    "arbitrary-node",

                "source":
                    "synthetic_provider",

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
):

    return {
        "source":
            source,

        "target":
            target,

        "type":
            "DEPENDS_ON",

        "confidence":
            0.99,

        "evidence":
            [
                "synthetic graph evidence"
            ],
    }


def make_engine():

    registry = AssetRegistry()

    for asset in (
        make_asset(
            "nebula-api",
            "api-random",
            group="nebula",
        ),
        make_asset(
            "nebula-db",
            "database-random",
            group="nebula",
        ),
        make_asset(
            "nebula-cache",
            "cache-random",
            group="nebula",
        ),
        make_asset(
            "unrelated",
            "unrelated-random",
        ),
    ):

        registry.register(
            asset
        )

    resolver = SemanticEntityResolver(
        registry
    )

    graph_query = (
        SemanticGraphQueryService(
            registry,
            graph=FakeGraph(
                [
                    relation(
                        "nebula-api",
                        "nebula-db",
                    ),
                    relation(
                        "nebula-api",
                        "nebula-cache",
                    ),
                ]
            ),
            entity_resolver=resolver,
        )
    )

    api = SimpleNamespace(
        registry=registry
    )

    return SemanticQueryEngine(
        api=api,
        entity_resolver=resolver,
        graph_query=graph_query,
    )


def test_de_que_depende_is_outgoing_dependency():

    engine = make_engine()

    plan = engine.plan(
        "¿De qué depende nebula?"
    )

    assert (
        plan.operation
        == "RELATION"
    )

    assert (
        plan.relationship
        == "DEPENDS_ON"
    )

    assert (
        plan.orientation
        == "OUTGOING"
    )

    assert (
        plan.entity_text
        == "nebula"
    )

    assert (
        plan.confidence
        >= 0.90
    )

    result = engine.query(
        "¿De qué depende nebula?"
    )

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert (
        result["semantic"]["intent"]
        == "RELATION"
    )

    assert (
        result["entity"]["kind"]
        == "GROUP"
    )

    assert result["count"] == 2


def test_que_depende_de_is_incoming_dependency():

    engine = make_engine()

    plan = engine.plan(
        "¿Qué depende de database-random?"
    )

    assert (
        plan.operation
        == "RELATION"
    )

    assert (
        plan.orientation
        == "INCOMING"
    )

    result = engine.query(
        "¿Qué depende de database-random?"
    )

    assert result["count"] == 1

    item = result[
        "results"
    ][0]

    assert (
        item["source_asset_id"]
        == "nebula-api"
    )

    assert (
        item["target_asset_id"]
        == "nebula-db"
    )


def test_dependency_noun_form_is_outgoing():

    engine = make_engine()

    plan = engine.plan(
        "¿Cuáles son las dependencias de nebula?"
    )

    assert (
        plan.operation
        == "RELATION"
    )

    assert (
        plan.orientation
        == "OUTGOING"
    )


def test_english_dependency_language_uses_same_graph_contract():

    engine = make_engine()

    outgoing = engine.plan(
        "What does nebula depend on?"
    )

    incoming = engine.plan(
        "What depends on database-random?"
    )

    assert (
        outgoing.relationship
        == "DEPENDS_ON"
    )

    assert (
        outgoing.orientation
        == "OUTGOING"
    )

    assert (
        incoming.relationship
        == "DEPENDS_ON"
    )

    assert (
        incoming.orientation
        == "INCOMING"
    )


def test_relation_question_without_concrete_target_needs_target():

    engine = make_engine()

    plan = engine.plan(
        "¿Qué depende de qué?"
    )

    assert (
        plan.operation
        == "RELATION"
    )

    assert (
        plan.relationship
        == "DEPENDS_ON"
    )

    assert (
        plan.orientation
        == "INCOMING"
    )

    assert plan.entity_text is None
    assert plan.target is None

    result = engine.query(
        "¿Qué depende de qué?"
    )

    assert (
        result["status"]
        == "NEEDS_TARGET"
    )


def test_english_relation_without_concrete_target_needs_target():

    engine = make_engine()

    result = engine.query(
        "What depends on what?"
    )

    assert (
        result["status"]
        == "NEEDS_TARGET"
    )
