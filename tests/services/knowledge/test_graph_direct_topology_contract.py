from types import SimpleNamespace

from atlas.services.assets.topology_traversal import (
    TopologyTraversalService,
)
from atlas.services.knowledge.graph import (
    GraphService,
)
from atlas.services.knowledge.engine import (
    KnowledgeEngine,
)


class FakeGraphRepository:

    def __init__(self):

        self.children = {
            "canonical-app": [
                {
                    "source": "canonical-app",
                    "target": "database",
                    "type": "DEPENDS_ON",
                    "metadata": {},
                    "confidence": 1.0,
                    "evidence": [],
                }
            ]
        }

        self.parents = {
            "canonical-app": [
                {
                    "source": "frontend",
                    "target": "canonical-app",
                    "type": "DEPENDS_ON",
                    "metadata": {},
                    "confidence": 1.0,
                    "evidence": [],
                }
            ]
        }

    def get_children(
        self,
        asset_id,
    ):
        return list(
            self.children.get(
                asset_id,
                []
            )
        )

    def get_parents(
        self,
        asset_id,
    ):
        return list(
            self.parents.get(
                asset_id,
                []
            )
        )

    def get_neighbors(
        self,
        asset_id,
    ):
        return (
            self.get_parents(
                asset_id
            )
            + self.get_children(
                asset_id
            )
        )


def topology():

    service = (
        TopologyTraversalService
        .__new__(
            TopologyTraversalService
        )
    )

    service.graph = (
        FakeGraphRepository()
    )

    service._resolve_graph_asset_id = (
        lambda asset_id:
            "canonical-app"
    )

    return service


def test_direct_dependencies_keep_graph_relationship_shape():

    result = (
        topology()
        .get_dependencies(
            "logical-app"
        )
    )

    assert result == [
        {
            "source":
                "canonical-app",

            "target":
                "database",

            "type":
                "DEPENDS_ON",

            "metadata":
                {},

            "confidence":
                1.0,

            "evidence":
                [],
        }
    ]


def test_direct_dependents_keep_graph_relationship_shape():

    result = (
        topology()
        .get_dependents(
            "logical-app"
        )
    )

    assert result == [
        {
            "source":
                "frontend",

            "target":
                "canonical-app",

            "type":
                "DEPENDS_ON",

            "metadata":
                {},

            "confidence":
                1.0,

            "evidence":
                [],
        }
    ]


def test_direct_neighbors_combine_both_directions():

    result = (
        topology()
        .get_neighbors(
            "logical-app"
        )
    )

    assert {
        (
            item["source"],
            item["target"],
        )
        for item in result
    } == {
        (
            "frontend",
            "canonical-app",
        ),
        (
            "canonical-app",
            "database",
        ),
    }


def test_knowledge_engine_build_uses_graph_compatibility_contract():

    graph = GraphService.__new__(
        GraphService
    )

    graph.topology = topology()

    engine = KnowledgeEngine.__new__(
        KnowledgeEngine
    )

    engine.graph = graph

    engine.factory = SimpleNamespace(
        get=lambda asset_type: None
    )

    asset = SimpleNamespace(
        id="logical-app",
        name="app",
        type=SimpleNamespace(
            name="APPLICATION"
        ),
        asset_roles=[],
        criticality=SimpleNamespace(
            name="MEDIUM"
        ),
        capabilities=[],
        role_weight=lambda: 1,
    )

    card = engine.build(
        asset
    )

    assert card.dependencies == [
        "database"
    ]

    assert card.dependents == [
        "frontend"
    ]

    assert (
        card.relationship_count
        == 2
    )
