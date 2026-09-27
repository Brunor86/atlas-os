from atlas.core.asset import (
    AssetStatus,
)

from atlas.services.semantic.query import (
    SemanticQueryEngine,
)


def test_semantic_query_impact_resolves_canonical_target(
    semantic_runtime,
):

    engine = semantic_runtime[
        "engine"
    ]

    target = semantic_runtime[
        "target"
    ]

    result = engine.query(
        "¿Qué pasa si cae node-alpha?"
    )

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert (
        result["semantic"]["intent"]
        == "IMPACT"
    )

    assert (
        result["semantic"]["target"]
        == target
    )

    assert (
        result["asset"]["id"]
        == target
    )

    assert (
        result["asset"]["name"]
        == "node-alpha"
    )


def test_dependency_language_is_not_generic_topology(
    semantic_runtime,
):

    engine = semantic_runtime[
        "engine"
    ]

    target = semantic_runtime[
        "target"
    ]

    dependent = semantic_runtime[
        "dependent"
    ]

    plan = engine.plan(
        "¿Qué depende de node-alpha?"
    )

    assert (
        plan.operation
        == "RELATION"
    )

    assert (
        plan.target
        == target
    )

    assert (
        plan.relationship
        == "DEPENDS_ON"
    )

    assert (
        plan.orientation
        == "INCOMING"
    )

    result = engine.query(
        "¿Qué depende de node-alpha?"
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
        result["semantic"]["relationship"]
        == "DEPENDS_ON"
    )

    assert (
        result["semantic"]["orientation"]
        == "INCOMING"
    )

    assert (
        result["count"]
        == 1
    )

    edge = result[
        "results"
    ][0]

    assert (
        edge["source_asset_id"]
        == dependent
    )

    assert (
        edge["target_asset_id"]
        == target
    )


def test_semantic_query_runs_on_resolves_canonical_target(
    semantic_runtime,
):

    engine = semantic_runtime[
        "engine"
    ]

    target = semantic_runtime[
        "target"
    ]

    result = engine.query(
        "¿Qué corre en node-alpha?"
    )

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert (
        result["semantic"]["target"]
        == target
    )

    assert (
        result["asset"]["id"]
        == target
    )

    assert (
        result["direction"]
        == "downstream"
    )

    assert (
        result["results"]
    )


def test_semantic_plan_resolves_canonical_target(
    semantic_runtime,
):

    engine = semantic_runtime[
        "engine"
    ]

    target = semantic_runtime[
        "target"
    ]

    plan = engine.plan(
        "¿Qué pasa si cae node-alpha?"
    )

    assert (
        plan.operation
        == "IMPACT"
    )

    assert (
        plan.target
        == target
    )

    assert (
        plan.confidence
        >= 0.9
    )


def test_semantic_query_and_plan_agree_on_target(
    semantic_runtime,
):

    engine = semantic_runtime[
        "engine"
    ]

    target = semantic_runtime[
        "target"
    ]

    question = (
        "¿Qué pasa si cae node-alpha?"
    )

    plan = engine.plan(
        question
    )

    result = engine.query(
        question
    )

    assert (
        plan.target
        == target
    )

    assert (
        result["semantic"]["target"]
        == target
    )

    assert (
        result["asset"]["id"]
        == target
    )



def test_semantic_plan_preserves_multiple_asset_types(
    semantic_runtime,
):

    engine = semantic_runtime[
        "engine"
    ]

    plan = engine.plan(
        "Mostrame servidores y máquinas virtuales"
    )

    assert (
        plan.operation
        == "ASSETS"
    )

    assert (
        plan.asset_type
        is None
    )

    assert set(
        plan.asset_types
    ) == {
        "SERVER",
        "VM",
    }


def test_semantic_query_unions_multiple_asset_types(
    semantic_runtime,
):

    engine = semantic_runtime[
        "engine"
    ]

    result = engine.query(
        "Mostrame máquinas virtuales y servicios"
    )

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert (
        result["semantic"]["intent"]
        == "INVENTORY"
    )

    assert set(
        result["semantic"][
            "asset_types"
        ]
    ) == {
        "VM",
        "SERVICE",
    }

    assert (
        result["count"]
        == 2
    )

    assert {
        asset["name"]
        for asset in result[
            "assets"
        ]
    } == {
        "node-alpha",
        "runtime-alpha",
    }



def test_structured_inventory_executor_supports_broad_inventory(
    semantic_runtime,
):

    engine = semantic_runtime[
        "engine"
    ]

    result = (
        engine
        .query_inventory_selectors(
            question=(
                "synthetic broad inventory"
            ),
            asset_types=[],
            statuses=[],
        )
    )

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert (
        result["semantic"][
            "intent"
        ]
        == "INVENTORY"
    )

    assert (
        result["semantic"][
            "asset_types"
        ]
        == []
    )

    assert (
        result["semantic"][
            "statuses"
        ]
        == []
    )

    assert (
        result["count"]
        == len(
            engine.registry.assets()
        )
    )


def test_structured_inventory_executor_unions_types_and_status(
    semantic_runtime,
):

    engine = semantic_runtime[
        "engine"
    ]

    registry = semantic_runtime[
        "registry"
    ]

    for asset in registry.assets():

        if asset.type.name in {
            "VM",
            "SERVICE",
        }:

            asset.status = (
                AssetStatus.ONLINE
            )

    result = (
        engine
        .query_inventory_selectors(
            question=(
                "synthetic typed inventory"
            ),
            asset_types=[
                "VM",
                "SERVICE",
            ],
            statuses=[
                "ONLINE",
            ],
        )
    )

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert set(
        result["semantic"][
            "asset_types"
        ]
    ) == {
        "VM",
        "SERVICE",
    }

    assert (
        result["semantic"][
            "statuses"
        ]
        == [
            "ONLINE",
        ]
    )

    assert {
        asset["type"]
        for asset in result[
            "assets"
        ]
    } == {
        "VM",
        "SERVICE",
    }

    assert all(
        asset["status"]
        == "ONLINE"
        for asset in result[
            "assets"
        ]
    )
