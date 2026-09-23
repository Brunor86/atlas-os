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
