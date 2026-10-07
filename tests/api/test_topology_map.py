from fastapi import FastAPI
from fastapi.testclient import TestClient

from atlas.core.asset import (
    Asset,
    AssetPresence,
    AssetStatus,
    AssetType,
)
from atlas.core.relationship import (
    Relationship,
    RelationshipType,
)
from atlas.storage.asset_repository import (
    AssetRepository,
)
from atlas.storage.graph_repository import (
    GraphRepository,
)


def seed_topology():

    assets = AssetRepository()
    graph = GraphRepository()

    host = Asset(
        id="server-alpha",
        name="atlas-alpha",
        type=AssetType.SERVER,
        status=AssetStatus.ONLINE,
        metadata={
            "hostname":
                "atlas-alpha",
        },
    )

    vm = Asset(
        id="vm-alpha",
        name="vm-alpha",
        type=AssetType.VM,
        status=AssetStatus.ONLINE,
        metadata={
            "vmid":
                100,
        },
    )

    app = Asset(
        id="application-alpha",
        name="app-alpha",
        type=AssetType.APPLICATION,
        status=AssetStatus.OFFLINE,
    )

    stale = Asset(
        id="application-stale",
        name="stale-alpha",
        type=AssetType.APPLICATION,
        status=AssetStatus.OFFLINE,
        presence=AssetPresence.STALE,
    )

    for asset in (
        host,
        vm,
        app,
        stale,
    ):
        assets.save_asset(
            asset
        )


    graph.save_relationship(
        Relationship(
            source=host.id,
            target=vm.id,
            type=RelationshipType.HOSTS,
            confidence=0.98,
        )
    )

    graph.save_relationship(
        Relationship(
            source=vm.id,
            target=app.id,
            type=RelationshipType.RUNS,
            confidence=0.95,
        )
    )

    graph.save_relationship(
        Relationship(
            source=host.id,
            target=stale.id,
            type=RelationshipType.HOSTS,
            confidence=0.50,
        )
    )

    return {
        "host":
            host,

        "vm":
            vm,

        "app":
            app,

        "stale":
            stale,
    }


def test_topology_map_exposes_active_graph_only():

    from atlas.services.assets.topology_map import (
        TopologyMapService,
    )

    topology = seed_topology()

    payload = (
        TopologyMapService()
        .snapshot()
    )

    assert (
        payload["status"]
        == "SUCCESS"
    )

    assert (
        payload["summary"]["nodes"]
        == 3
    )

    assert (
        payload["summary"]["edges"]
        == 2
    )

    assert (
        payload["summary"]["connected_nodes"]
        == 3
    )

    assert (
        payload["summary"]["unconnected_nodes"]
        == 0
    )


    ids = {
        node["id"]
        for node in payload[
            "nodes"
        ]
    }

    assert ids == {
        topology["host"].id,
        topology["vm"].id,
        topology["app"].id,
    }

    assert (
        topology["stale"].id
        not in ids
    )


    edges = {
        (
            edge["source"],
            edge["type"],
            edge["target"],
        )
        for edge in payload[
            "edges"
        ]
    }

    assert edges == {
        (
            topology["host"].id,
            "HOSTS",
            topology["vm"].id,
        ),
        (
            topology["vm"].id,
            "RUNS",
            topology["app"].id,
        ),
    }


def test_topology_map_exposes_operational_node_metadata():

    topology = seed_topology()

    from atlas.services.assets.topology_map import (
        TopologyMapService,
    )

    payload = (
        TopologyMapService()
        .snapshot()
    )

    nodes = {
        node["id"]:
            node
        for node in payload[
            "nodes"
        ]
    }

    host = nodes[
        topology["host"].id
    ]

    vm = nodes[
        topology["vm"].id
    ]

    assert (
        host["status"]
        == "ONLINE"
    )

    assert (
        host["network"]["hostname"]
        == "atlas-alpha"
    )

    assert (
        vm["network"]["vmid"]
        == 100
    )


def test_topology_map_summary_is_deterministic():

    seed_topology()

    from atlas.services.assets.topology_map import (
        TopologyMapService,
    )

    payload = (
        TopologyMapService()
        .snapshot()
    )

    assert payload[
        "summary"
    ][
        "by_type"
    ] == {
        "APPLICATION": 1,
        "SERVER": 1,
        "VM": 1,
    }

    assert payload[
        "summary"
    ][
        "by_status"
    ] == {
        "OFFLINE": 1,
        "ONLINE": 2,
    }

    assert payload[
        "summary"
    ][
        "by_relationship"
    ] == {
        "HOSTS": 1,
        "RUNS": 1,
    }


def test_topology_map_endpoint_is_read_only():

    seed_topology()

    from atlas.api.topology import (
        router,
    )

    app = FastAPI()

    app.include_router(
        router
    )

    with TestClient(
        app
    ) as client:

        response = client.get(
            "/api/topology/map"
        )

    assert (
        response.status_code
        == 200
    )

    payload = (
        response.json()
    )

    assert (
        payload["status"]
        == "SUCCESS"
    )

    assert (
        payload["summary"]["nodes"]
        == 3
    )

    assert (
        payload["summary"]["edges"]
        == 2
    )
