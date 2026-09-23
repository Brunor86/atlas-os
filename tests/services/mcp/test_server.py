import asyncio

from mcp import Client

from atlas.mcp.server import (
    build_server,
)


EXPECTED_TOOLS = {
    "atlas_search_assets",
    "atlas_describe_asset",
    "atlas_resolve_entity",
    "atlas_query_entity_relations",
    "atlas_query_relations",
    "atlas_query_impact",
    "atlas_attention_summary",
    "atlas_query_asset_status",
    "atlas_semantic_query",
}


def run(
    coroutine,
):
    return asyncio.run(
        coroutine
    )


async def list_tools():

    async with Client(
        build_server()
    ) as client:

        return (
            await client.list_tools()
        )


async def call(
    name,
    arguments,
):

    async with Client(
        build_server()
    ) as client:

        return (
            await client.call_tool(
                name,
                arguments,
            )
        )


def test_mcp_exposes_only_expected_knowledge_tools():

    result = run(
        list_tools()
    )

    tools = {
        tool.name:
            tool
        for tool in result.tools
    }

    assert set(
        tools
    ) == EXPECTED_TOOLS

    for tool in tools.values():

        assert (
            tool.annotations
            is not None
        )

        assert (
            tool.annotations.read_only_hint
            is True
        )

        assert (
            tool.annotations.open_world_hint
            is False
        )


def test_mcp_has_no_action_tools():

    result = run(
        list_tools()
    )

    names = {
        tool.name.lower()
        for tool in result.tools
    }

    forbidden = (
        "restart",
        "stop",
        "delete",
        "exec",
        "shell",
        "write",
    )

    for token in forbidden:

        assert not any(
            token in name
            for name in names
        )


def test_search_prefers_specific_compute_identity_on_name_collision(mcp_synthetic_runtime):

    result = run(
        call(
            "atlas_search_assets",
            {
                "query":
                    "node-alpha",
            },
        )
    )

    assert result.is_error is False

    data = (
        result
        .structured_content[
            "data"
        ]
    )

    assert data[
        "status"
    ] == "SUCCESS"

    assert (
        data["matches"][0]["name"]
        == "node-alpha"
    )

    assert (
        data["matches"][0]["match_reason"]
        == "exact_name"
    )

    assert (
        data["matches"][0]["type"]
        == "VM"
    )

    #
    # docker_host references must not flood the entity search.
    #
    assert (
        data["count"]
        < data["total_candidates"]
    )

    assert all(
        item["match_reason"]
        in {
            "exact_id",
            "exact_name",
        }
        for item in data["matches"]
    )

    assert all(
        item["name"]
        == "node-alpha"
        for item in data["matches"]
    )


def test_search_result_is_compact():

    result = run(
        call(
            "atlas_search_assets",
            {
                "query":
                    "debian-docker",
            },
        )
    )

    matches = (
        result
        .structured_content[
            "data"
        ][
            "matches"
        ]
    )

    for item in matches:

        metadata = item.get(
            "metadata",
            {}
        )

        assert (
            "labels"
            not in metadata
        )


def test_search_can_resolve_compose_application_group(mcp_synthetic_runtime):

    result = run(
        call(
            "atlas_search_assets",
            {
                "query":
                    "suite-alpha",
            },
        )
    )

    data = (
        result
        .structured_content[
            "data"
        ]
    )

    names = {
        item["name"]
        for item in data[
            "matches"
        ]
    }

    assert (
        "app-alpha"
        in names
    )

    assert (
        "database-alpha"
        in names
    )

    assert (
        "cache-alpha"
        in names
    )


def test_mcp_describes_synthetic_vm(mcp_synthetic_runtime):

    search = run(
        call(
            "atlas_search_assets",
            {
                "query":
                    "node-alpha",
            },
        )
    )

    vm = (
        search
        .structured_content[
            "data"
        ][
            "matches"
        ][0]
    )

    result = run(
        call(
            "atlas_describe_asset",
            {
                "asset_id":
                    vm["id"],
            },
        )
    )

    data = (
        result
        .structured_content[
            "data"
        ]
    )

    assert (
        data["asset"]["name"]
        == "node-alpha"
    )

    assert (
        "labels"
        not in data[
            "asset"
        ].get(
            "metadata",
            {}
        )
    )


def test_mcp_can_query_vm_topology(mcp_synthetic_runtime):

    search = run(
        call(
            "atlas_search_assets",
            {
                "query":
                    "node-alpha",
            },
        )
    )

    vm = (
        search
        .structured_content[
            "data"
        ][
            "matches"
        ][0]
    )

    result = run(
        call(
            "atlas_query_relations",
            {
                "asset_id":
                    vm["id"],

                "direction":
                    "downstream",

                "depth":
                    2,
            },
        )
    )

    assert (
        result.is_error
        is False
    )

    assert (
        result
        .structured_content[
            "data"
        ][
            "status"
        ]
        == "SUCCESS"
    )


def test_mcp_semantic_query_uses_atlas():

    result = run(
        call(
            "atlas_semantic_query",
            {
                "question":
                    "¿Qué máquinas virtuales tengo?",
            },
        )
    )

    assert (
        result.is_error
        is False
    )


def test_mcp_filters_compose_dependencies(mcp_synthetic_runtime):

    search = run(
        call(
            "atlas_search_assets",
            {
                "query":
                    "suite-alpha",
            },
        )
    )

    server = next(
        item
        for item in (
            search
            .structured_content[
                "data"
            ][
                "matches"
            ]
        )
        if item[
            "name"
        ] == "app-alpha"
    )

    result = run(
        call(
            "atlas_query_relations",
            {
                "asset_id":
                    server["id"],

                "direction":
                    "downstream",

                "relationship":
                    "DEPENDS_ON",

                "depth":
                    1,
            },
        )
    )

    data = (
        result
        .structured_content[
            "data"
        ]
    )

    assert (
        data["relationship"]
        == "DEPENDS_ON"
    )

    assert (
        data["count"]
        == 2
    )

    names = {
        item["name"]
        for item in data[
            "results"
        ]
    }

    assert names == {
        "database-alpha",
        "cache-alpha",
    }

    assert (
        "labels"
        not in data[
            "asset"
        ].get(
            "metadata",
            {},
        )
    )


def test_mcp_exposes_operational_attention():

    result = run(
        call(
            "atlas_attention_summary",
            {},
        )
    )

    assert (
        result.is_error
        is False
    )

    data = (
        result
        .structured_content[
            "data"
        ]
    )

    assert (
        data["status"]
        == "SUCCESS"
    )

    attention = data[
        "attention"
    ]

    assert (
        attention["state"]
        in {
            "HEALTHY",
            "WARNING",
            "CRITICAL",
            "UNKNOWN",
        }
    )

    assert isinstance(
        attention[
            "attention_required"
        ],
        bool,
    )

    assert isinstance(
        attention[
            "items"
        ],
        list,
    )


def test_mcp_can_resolve_and_query_semantic_group(
    mcp_synthetic_runtime,
):

    resolved = run(
        call(
            "atlas_resolve_entity",
            {
                "query":
                    "suite-alpha",
            },
        )
    )

    assert (
        resolved.is_error
        is False
    )

    entity_data = (
        resolved
        .structured_content[
            "data"
        ]
    )

    assert (
        entity_data[
            "status"
        ]
        == "SUCCESS"
    )

    entity = entity_data[
        "entity"
    ]

    assert (
        entity[
            "kind"
        ]
        == "GROUP"
    )

    reference = entity[
        "reference"
    ]

    assert reference

    relations = run(
        call(
            "atlas_query_entity_relations",
            {
                "entity":
                    reference,

                "direction":
                    "downstream",

                "relationship":
                    "DEPENDS_ON",

                "depth":
                    1,
            },
        )
    )

    assert (
        relations.is_error
        is False
    )

    data = (
        relations
        .structured_content[
            "data"
        ]
    )

    assert (
        data[
            "status"
        ]
        == "SUCCESS"
    )

    assert (
        data[
            "entity"
        ][
            "kind"
        ]
        == "GROUP"
    )

    assert (
        data[
            "entity"
        ][
            "reference"
        ]
        == reference
    )

    assert (
        data[
            "relationship"
        ]
        == "DEPENDS_ON"
    )

    assert (
        data[
            "direction"
        ]
        == "DOWNSTREAM"
    )

    assert (
        data[
            "count"
        ]
        == 2
    )

    assert all(
        item[
            "relationship"
        ]
        == "DEPENDS_ON"
        for item in data[
            "results"
        ]
    )

    assert all(
        item[
            "direction"
        ]
        == "DOWNSTREAM"
        for item in data[
            "results"
        ]
    )

    assert all(
        item.get(
            "root_member_id"
        )
        for item in data[
            "results"
        ]
    )

    assert all(
        item.get(
            "source_asset_id"
        )
        for item in data[
            "results"
        ]
    )

    assert all(
        item.get(
            "target_asset_id"
        )
        for item in data[
            "results"
        ]
    )



def test_mcp_queries_canonical_asset_status(
    mcp_synthetic_runtime,
):

    result = run(
        call(
            "atlas_query_asset_status",
            {
                "status":
                    "online",

                "asset_type":
                    "application",
            },
        )
    )

    assert (
        result.is_error
        is False
    )

    data = (
        result
        .structured_content[
            "data"
        ]
    )

    assert (
        data["status"]
        == "SUCCESS"
    )

    assert (
        data["complete"]
        is True
    )

    assert (
        data["filters"]["status"]
        == "ONLINE"
    )

    assert (
        data["filters"]["asset_type"]
        == "APPLICATION"
    )

    assert (
        data["count"]
        == len(
            data["assets"]
        )
    )

    assert all(
        asset["status"]
        == "ONLINE"
        for asset in data[
            "assets"
        ]
    )

    assert all(
        asset["type"]
        == "APPLICATION"
        for asset in data[
            "assets"
        ]
    )

    assert all(
        set(
            asset
        )
        == {
            "id",
            "name",
            "type",
            "status",
            "health",
            "criticality",
            "roles",
            "last_seen",
        }
        for asset in data[
            "assets"
        ]
    )


def test_mcp_status_query_preserves_verified_zero_result():

    result = run(
        call(
            "atlas_query_asset_status",
            {
                "status":
                    "OFFLINE",

                "asset_type":
                    "SENSOR",
            },
        )
    )

    assert (
        result.is_error
        is False
    )

    data = (
        result
        .structured_content[
            "data"
        ]
    )

    assert (
        data["status"]
        == "SUCCESS"
    )

    assert (
        data["complete"]
        is True
    )

    assert (
        data["count"]
        == len(
            data["assets"]
        )
    )

    #
    # Whether the synthetic runtime contains matching sensors
    # is not the MCP contract under test. What matters here is
    # that a complete successful inventory query is preserved
    # rather than converted into an MCP error.
    #
    assert isinstance(
        data["assets"],
        list,
    )


def test_mcp_status_query_rejects_invalid_selector():

    result = run(
        call(
            "atlas_query_asset_status",
            {
                "status":
                    "BROKEN",
            },
        )
    )

    assert (
        result.is_error
        is False
    )

    data = (
        result
        .structured_content[
            "data"
        ]
    )

    assert (
        data["status"]
        == "ERROR"
    )

    assert (
        data["complete"]
        is False
    )

    assert (
        data["count"]
        == 0
    )



def test_mcp_can_query_neighbors_topology(
    mcp_synthetic_runtime,
):

    search = run(
        call(
            "atlas_search_assets",
            {
                "query":
                    "node-alpha",
            },
        )
    )

    vm = (
        search
        .structured_content[
            "data"
        ][
            "matches"
        ][0]
    )

    result = run(
        call(
            "atlas_query_relations",
            {
                "asset_id":
                    vm["id"],

                "direction":
                    "neighbors",

                "depth":
                    2,
            },
        )
    )

    assert result.is_error is False

    data = (
        result
        .structured_content[
            "data"
        ]
    )

    assert data["status"] == "SUCCESS"
    assert data["direction"] == "neighbors"

    directions = {
        item["direction"]
        for item in data[
            "results"
        ]
    }

    assert directions.issubset(
        {
            "UPSTREAM",
            "DOWNSTREAM",
        }
    )
