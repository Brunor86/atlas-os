from types import SimpleNamespace
from unittest.mock import Mock, patch

from atlas.services.assets.topology_traversal import (
    TopologyTraversalService,
)
from atlas.services.noc.impact import ImpactEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeGraph:
    def __init__(self):
        self.parents = {}
        self.children = {}

    def get_parents(self, asset_id):
        return list(self.parents.get(asset_id, []))

    def get_children(self, asset_id):
        return list(self.children.get(asset_id, []))


class FakeAssets:
    def __init__(self, assets):
        self.assets = assets

    def get_asset(self, asset_id):
        for asset in self.assets:
            if asset.id == asset_id:
                return asset
        return None

    def get_all_assets(self):
        return list(self.assets)


def make_asset(
    asset_id,
    name,
    criticality="MEDIUM",
    roles=None,
):
    criticality_obj = SimpleNamespace(
        name=criticality,
    )

    role_objects = [
        SimpleNamespace(name=role)
        for role in (roles or [])
    ]

    return SimpleNamespace(
        id=asset_id,
        name=name,
        criticality=criticality_obj,
        asset_roles=role_objects,
    )


def make_topology(assets):
    topology = object.__new__(
        TopologyTraversalService
    )

    topology.graph = FakeGraph()
    topology.assets = FakeAssets(assets)

    return topology


# ---------------------------------------------------------------------------
# Topology identity resolution
# ---------------------------------------------------------------------------


def test_topology_resolves_logical_name_to_graph_connected_asset():

    canonical = make_asset(
        "application-docker-nginx-123",
        "nginx",
    )

    logical = make_asset(
        "application-nginx",
        "nginx",
    )

    topology = make_topology(
        [
            logical,
            canonical,
        ]
    )

    topology.graph.parents[
        "application-docker-nginx-123"
    ] = [
        {
            "source": "vm-100",
            "type": "DEPENDS_ON",
        }
    ]

    resolved = topology._resolve_graph_asset_id(
        "nginx"
    )

    assert resolved == "application-docker-nginx-123"


def test_topology_keeps_existing_graph_identity():

    asset = make_asset(
        "application-docker-nginx-123",
        "nginx",
    )

    topology = make_topology([asset])

    topology.graph.children[
        "application-docker-nginx-123"
    ] = [
        {
            "target": "service-web",
            "type": "RUNS",
        }
    ]

    resolved = topology._resolve_graph_asset_id(
        "application-docker-nginx-123"
    )

    assert resolved == "application-docker-nginx-123"


def test_topology_returns_original_id_when_asset_is_unknown():

    topology = make_topology([])

    resolved = topology._resolve_graph_asset_id(
        "does-not-exist"
    )

    assert resolved == "does-not-exist"


# ---------------------------------------------------------------------------
# Downstream traversal
# ---------------------------------------------------------------------------


def test_downstream_traversal_walks_children():

    asset = make_asset(
        "app-1",
        "application",
    )

    topology = make_topology([asset])

    topology.graph.children["app-1"] = [
        {
            "target": "container-1",
            "type": "RUNS",
            "confidence": 0.9,
            "evidence": ["docker state"],
        }
    ]

    topology.graph.children["container-1"] = [
        {
            "target": "service-1",
            "type": "DEPENDS_ON",
            "confidence": 0.8,
            "evidence": ["service relation"],
        }
    ]

    with patch(
        "atlas.services.assets.topology_traversal.RelationshipType"
    ) as relationship_enum:

        relationship_enum.__getitem__.side_effect = (
            lambda name: name
        )

        with patch(
            "atlas.services.assets.topology_traversal.relationship_impact_score",
            return_value=10,
        ):

            result = topology.downstream(
                "app-1",
                depth=5,
            )

    ids = [
        item["asset_id"]
        for item in result
    ]

    assert ids == [
        "container-1",
        "service-1",
    ]

    assert result[0]["depth"] == 1
    assert result[1]["depth"] == 2


# ---------------------------------------------------------------------------
# Blast radius
# ---------------------------------------------------------------------------


def test_blast_radius_excludes_upstream_assets():

    asset = make_asset(
        "application-docker-nginx-123",
        "nginx",
    )

    topology = make_topology([asset])

    topology.graph.parents[
        "application-docker-nginx-123"
    ] = [
        {
            "source": "vm-100",
            "type": "HOSTED_ON",
        }
    ]

    topology.graph.children[
        "application-docker-nginx-123"
    ] = [
        {
            "target": "client-1",
            "type": "DEPENDS_ON",
            "confidence": 1.0,
            "evidence": ["dependency"],
        }
    ]

    with patch(
        "atlas.services.assets.topology_traversal.RelationshipType"
    ) as relationship_enum:

        relationship_enum.__getitem__.side_effect = (
            lambda name: name
        )

        with patch(
            "atlas.services.assets.topology_traversal.relationship_impact_score",
            return_value=10,
        ):

            result = topology.blast_radius(
                "application-docker-nginx-123",
                depth=5,
            )

    ids = {
        item["asset"]
        for item in result
    }

    assert "client-1" in ids
    assert "vm-100" not in ids


# ---------------------------------------------------------------------------
# Impact scoring
# ---------------------------------------------------------------------------


def test_impact_does_not_add_upstream_to_impact_score():

    asset = make_asset(
        "app-1",
        "NPM",
        criticality="LOW",
    )

    engine = object.__new__(
        ImpactEngine
    )

    engine.assets = FakeAssets([asset])

    upstream = [
        {
            "asset_id": "vm-100",
            "relationship": "HOSTED_ON",
            "depth": 1,
            "confidence": 1.0,
            "relationship_weight": 10,
            "impact_score": 10,
            "evidence": [],
        },
        {
            "asset_id": "proxmox",
            "relationship": "HOSTED_ON",
            "depth": 2,
            "confidence": 1.0,
            "relationship_weight": 10,
            "impact_score": 5,
            "evidence": [],
        },
    ]

    engine.topology = Mock()

    engine.topology.critical_upstream.return_value = upstream
    engine.topology.downstream.return_value = []

    result = engine.analyze(
        "app-1"
    )

    assert result["impact_score"] == 10
    assert result["severity"] == "LOW"


def test_impact_adds_downstream_blast_radius():

    asset = make_asset(
        "app-1",
        "NPM",
        criticality="LOW",
    )

    engine = object.__new__(
        ImpactEngine
    )

    engine.assets = FakeAssets([asset])

    engine.topology = Mock()

    engine.topology.critical_upstream.return_value = []

    engine.topology.downstream.return_value = [
        {"asset_id": "client-1"},
        {"asset_id": "client-2"},
        {"asset_id": "client-3"},
    ]

    result = engine.analyze(
        "app-1"
    )

    assert result["impact_score"] == 40
    assert result["severity"] == "MEDIUM"


def test_criticality_and_roles_contribute_to_impact():

    asset = make_asset(
        "db-1",
        "MariaDB",
        criticality="HIGH",
        roles=["DATABASE_SERVER"],
    )

    engine = object.__new__(
        ImpactEngine
    )

    engine.assets = FakeAssets([asset])

    engine.topology = Mock()

    engine.topology.critical_upstream.return_value = []
    engine.topology.downstream.return_value = []

    result = engine.analyze(
        "db-1"
    )

    assert result["impact_score"] == 110
    assert result["severity"] == "CRITICAL"


def test_missing_asset_returns_error():

    engine = object.__new__(
        ImpactEngine
    )

    engine.assets = FakeAssets([])
    engine.topology = Mock()

    result = engine.analyze(
        "missing"
    )

    assert result == {
        "error": "asset not found"
    }
