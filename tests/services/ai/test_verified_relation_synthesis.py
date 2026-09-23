from types import SimpleNamespace

from atlas.services.ai.agent.agent import (
    OperatorAgent,
)


def test_neighbors_relations_are_synthesized_without_llm_final():

    result = SimpleNamespace(
        success=True,
        data={
            "asset": {
                "name": "debian-docker",
            },
            "results": [
                {
                    "name": "radarr",
                    "relationship": "RUNS",
                    "direction": "DOWNSTREAM",
                },
                {
                    "name": "prometheus",
                    "relationship": "MONITORS",
                    "direction": "UPSTREAM",
                },
            ],
        },
    )

    answer = (
        OperatorAgent
        ._verified_relation_answer(
            {
                "direction": "neighbors",
                "relationship": None,
            },
            result,
        )
    )

    assert answer is not None
    assert "debian-docker" in answer
    assert "DOWNSTREAM · RUNS · radarr" in answer
    assert (
        "UPSTREAM · MONITORS · prometheus"
        in answer
    )


def test_unfiltered_one_way_relation_query_keeps_planning():

    result = SimpleNamespace(
        success=True,
        data={
            "asset": {
                "name": "debian-docker",
            },
            "results": [
                {
                    "name": "radarr",
                    "relationship": "RUNS",
                    "direction": "DOWNSTREAM",
                },
            ],
        },
    )

    answer = (
        OperatorAgent
        ._verified_relation_answer(
            {
                "direction": "downstream",
                "relationship": None,
            },
            result,
        )
    )

    assert answer is None


def test_planner_prompt_explains_bidirectional_neighbors():

    agent = object.__new__(
        OperatorAgent
    )

    agent._tool_descriptions = (
        lambda: []
    )

    prompt = agent._build_prompt(
        (
            "Mostrame todas las relaciones "
            "entrantes y salientes"
        ),
        [],
    )

    assert 'direction="neighbors"' in prompt
    assert "incoming and outgoing" in prompt
