from types import SimpleNamespace

from atlas.services.semantic.api import (
    AtlasSemanticAPI,
)


class FakeTraversal:

    def upstream(
        self,
        asset_id,
        depth=5,
    ):

        assert asset_id == "vm-100"
        assert depth == 3

        return [
            {
                "asset_id": "prometheus",
                "relationship": "MONITORS",
                "direction": "UPSTREAM",
                "depth": 1,
            },
        ]

    def downstream(
        self,
        asset_id,
        depth=5,
    ):

        assert asset_id == "vm-100"
        assert depth == 3

        return [
            {
                "asset_id": "radarr",
                "relationship": "RUNS",
                "direction": "DOWNSTREAM",
                "depth": 1,
            },
        ]


class FakeSemanticAPI:

    _topology = FakeTraversal()

    @staticmethod
    def _resolve(
        asset_id,
    ):

        assert asset_id == "vm-100"

        return SimpleNamespace(
            id="vm-100",
        )

    @staticmethod
    def _asset_summary(
        asset,
    ):

        return {
            "id": asset.id,
            "name": "debian-docker",
        }


def test_neighbors_combines_upstream_and_downstream():

    api = FakeSemanticAPI()

    result = AtlasSemanticAPI.topology(
        api,
        "vm-100",
        direction="neighbors",
        depth=3,
    )

    assert result["status"] == "SUCCESS"
    assert result["direction"] == "neighbors"
    assert result["depth"] == 3

    rows = result["results"]

    assert len(rows) == 2

    directions = {
        row["direction"]
        for row in rows
    }

    assert directions == {
        "UPSTREAM",
        "DOWNSTREAM",
    }



class FakeDependencyTraversal:

    def downstream(
        self,
        asset_id,
        depth=5,
    ):

        return [
            {
                "asset_id": "database",
                "relationship": "DEPENDS_ON",
                "direction": "DOWNSTREAM",
                "depth": 1,
            },
            {
                "asset_id": "container",
                "relationship": "RUNS",
                "direction": "DOWNSTREAM",
                "depth": 1,
            },
        ]

    def upstream(
        self,
        asset_id,
        depth=5,
    ):

        return [
            {
                "asset_id": "frontend",
                "relationship": "DEPENDS_ON",
                "direction": "UPSTREAM",
                "depth": 1,
            },
            {
                "asset_id": "host",
                "relationship": "HOSTS",
                "direction": "UPSTREAM",
                "depth": 1,
            },
        ]


class FakeDependencySemanticAPI(
    FakeSemanticAPI
):

    _topology = (
        FakeDependencyTraversal()
    )


def test_dependencies_alias_filters_downstream_depends_on():

    api = FakeDependencySemanticAPI()

    result = AtlasSemanticAPI.topology(
        api,
        "vm-100",
        direction="dependencies",
        depth=3,
    )

    assert result["status"] == "SUCCESS"
    assert result["direction"] == "dependencies"

    assert [
        item["asset_id"]
        for item in result["results"]
    ] == [
        "database",
    ]


def test_dependents_alias_filters_upstream_depends_on():

    api = FakeDependencySemanticAPI()

    result = AtlasSemanticAPI.topology(
        api,
        "vm-100",
        direction="dependents",
        depth=3,
    )

    assert result["status"] == "SUCCESS"
    assert result["direction"] == "dependents"

    assert [
        item["asset_id"]
        for item in result["results"]
    ] == [
        "frontend",
    ]
