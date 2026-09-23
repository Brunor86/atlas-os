from atlas.core.asset import (
    AssetStatus,
)

from atlas.services.semantic.api import (
    AtlasSemanticAPI,
)

from atlas.services.assets.runtime import (
    get_asset_registry,
)


def test_semantic_api_asset(
    semantic_runtime,
):

    api = semantic_runtime[
        "api"
    ]

    target = semantic_runtime[
        "target"
    ]

    result = api.asset(
        target
    )

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert (
        result["asset"]["id"]
        == target
    )

    assert (
        result["asset"]["name"]
        == "node-alpha"
    )


def test_semantic_api_assets(
    semantic_runtime,
):

    api = semantic_runtime[
        "api"
    ]

    result = api.assets()

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert (
        result["count"]
        == len(
            result["assets"]
        )
    )

    assert (
        result["count"]
        == 4
    )


def test_semantic_api_find(
    semantic_runtime,
):

    api = semantic_runtime[
        "api"
    ]

    target = semantic_runtime[
        "target"
    ]

    result = api.find(
        "node-alpha"
    )

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert (
        result["count"]
        == len(
            result["matches"]
        )
    )

    assert any(
        item["id"] == target
        for item in result[
            "matches"
        ]
    )


def test_semantic_api_topology(
    semantic_runtime,
):

    api = semantic_runtime[
        "api"
    ]

    target = semantic_runtime[
        "target"
    ]

    result = api.topology(
        target,
        direction="downstream",
        depth=5,
    )

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert (
        result["asset"]["id"]
        == target
    )

    assert isinstance(
        result["results"],
        list,
    )

    relationships = {
        item["relationship"]
        for item in result[
            "results"
        ]
    }

    assert (
        "PROVIDES"
        in relationships
    )

    assert (
        "RUNS"
        in relationships
    )


def test_semantic_api_impact(
    semantic_runtime,
):

    api = semantic_runtime[
        "api"
    ]

    target = semantic_runtime[
        "target"
    ]

    result = api.impact(
        target
    )

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert (
        result["asset"]["id"]
        == target
    )

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


def test_semantic_api_infrastructure(
    semantic_runtime,
):

    api = semantic_runtime[
        "api"
    ]

    result = (
        api.infrastructure()
    )

    inventory = api.assets()

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert (
        inventory["status"]
        == "SUCCESS"
    )

    assert (
        result["total_assets"]
        == inventory["count"]
    )

    assert isinstance(
        result["inventory"],
        dict,
    )


def test_semantic_api_uses_runtime_registry():

    api = AtlasSemanticAPI()

    registry = (
        get_asset_registry()
    )

    assert (
        api.registry
        is registry
    )



def test_semantic_api_query_asset_status_filters_canonical_inventory(
    semantic_runtime,
):

    api = semantic_runtime[
        "api"
    ]

    application_id = semantic_runtime[
        "application"
    ]

    registry = semantic_runtime[
        "registry"
    ]

    application = next(
        asset
        for asset in registry.assets()
        if asset.id == application_id
    )

    application.status = (
        AssetStatus.OFFLINE
    )

    result = api.query_asset_status(
        status="offline",
        asset_type="application",
    )

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert (
        result["complete"]
        is True
    )

    assert (
        result["filters"]["status"]
        == "OFFLINE"
    )

    assert (
        result["filters"]["asset_type"]
        == "APPLICATION"
    )

    assert (
        result["count"]
        == 1
    )

    assert (
        result["assets"][0]["id"]
        == application_id
    )

    assert (
        result["assets"][0]["status"]
        == "OFFLINE"
    )


def test_semantic_api_query_asset_status_zero_is_complete_evidence(
    semantic_runtime,
):

    api = semantic_runtime[
        "api"
    ]

    result = api.query_asset_status(
        status="OFFLINE",
        asset_type="STORAGE",
    )

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert (
        result["complete"]
        is True
    )

    assert (
        result["count"]
        == 0
    )

    assert (
        result["assets"]
        == []
    )


def test_semantic_api_query_asset_status_rejects_unknown_status(
    semantic_runtime,
):

    api = semantic_runtime[
        "api"
    ]

    result = api.query_asset_status(
        status="BROKEN",
        asset_type="APPLICATION",
    )

    assert (
        result["status"]
        == "ERROR"
    )

    assert (
        result["complete"]
        is False
    )

    assert (
        result["count"]
        == 0
    )


def test_semantic_api_query_asset_status_rejects_unknown_type(
    semantic_runtime,
):

    api = semantic_runtime[
        "api"
    ]

    result = api.query_asset_status(
        status="OFFLINE",
        asset_type="MAGICAL_SERVER",
    )

    assert (
        result["status"]
        == "ERROR"
    )

    assert (
        result["complete"]
        is False
    )
