from atlas.services.semantic.query import SemanticQueryEngine


def test_empty_question():
    engine = SemanticQueryEngine()

    result = engine.query("")

    assert result["status"] == "ERROR"
    assert result["error"] == "question is required"


def test_impact_without_target():
    engine = SemanticQueryEngine()

    result = engine.query("¿Qué pasa si cae?")

    assert result["status"] == "NEEDS_TARGET"
    assert result["intent"] == "IMPACT"


def test_relation_without_target():
    engine = SemanticQueryEngine()

    result = engine.query(
        "¿Qué depende de qué?"
    )

    assert (
        result["status"]
        == "NEEDS_TARGET"
    )

    assert (
        result["intent"]
        == "RELATION"
    )


def test_unknown_asset():
    engine = SemanticQueryEngine()

    result = engine.query(
        "¿Qué pasa si cae servidor-que-no-existe?"
    )

    assert result["status"] in {
        "NEEDS_TARGET",
        "ERROR",
    }


def test_valid_query_still_resolves(
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
        result["asset"]["id"]
        == target
    )
    # This test validates that a valid semantic query resolves.
    # Exact impact severity belongs to ImpactEngine tests and must
    # not depend on the characteristics of a live infrastructure.
    assert isinstance(
        result["impact"],
        dict,
    )

    assert isinstance(
        result["impact"].get(
            "impact_score",
            0,
        ),
        (int, float),
    )

    assert result["impact"].get(
        "severity"
    )
