from types import SimpleNamespace
from unittest.mock import patch

from atlas.services.assets.topology_traversal import (
    TopologyTraversalService,
)


class FakeGraph:

    def __init__(self):
        self.parents = {}
        self.children = {}

    def get_parents(self, asset_id):
        return list(
            self.parents.get(
                asset_id,
                [],
            )
        )

    def get_children(self, asset_id):
        return list(
            self.children.get(
                asset_id,
                [],
            )
        )


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
):
    return SimpleNamespace(
        id=asset_id,
        name=name,
    )


def make_topology():

    topology = object.__new__(
        TopologyTraversalService
    )

    topology.graph = FakeGraph()

    topology.assets = FakeAssets(
        [
            make_asset(
                "app-1",
                "NPM",
            )
        ]
    )

    return topology


def test_critical_upstream_keeps_operational_dependencies():

    topology = make_topology()

    topology.graph.parents["app-1"] = [
        {
            "source": "vm-100",
            "type": "HOSTED_ON",
            "confidence": 0.9,
            "evidence": [
                "VM hosts application",
            ],
        },
        {
            "source": "unrelated-service",
            "type": "MONITORS",
            "confidence": 1.0,
            "evidence": [],
        },
    ]

    with patch(
        "atlas.services.assets.topology_traversal.RelationshipType"
    ) as relationship_enum:

        relationship_enum.__getitem__.side_effect = (
            lambda name: name
        )

        with patch(
            "atlas.services.assets.topology_traversal.is_operational_relationship",
            side_effect=lambda relationship: (
                relationship == "HOSTED_ON"
            ),
        ):

            with patch(
                "atlas.services.assets.topology_traversal.relationship_impact_score",
                return_value=10,
            ):

                result = topology.critical_upstream(
                    "app-1"
                )

    assert len(result) == 1

    assert result[0]["asset_id"] == "vm-100"

    assert result[0]["relationship"] == "HOSTED_ON"

    assert result[0]["direction"] == "UPSTREAM"

    assert result[0]["depth"] == 1

    assert result[0]["confidence"] == 0.9

    assert result[0]["evidence"] == [
        "VM hosts application"
    ]

    assert result[0]["relationship_weight"] == 10

    assert result[0]["impact_score"] == 9.0


def test_critical_upstream_ignores_system_services():

    topology = make_topology()

    # This test exercises traversal filtering, not provider-specific
    # service identity. System-service classification itself has a
    # separate domain-model regression test.
    topology._is_system_service = (
        lambda asset_id: (
            asset_id
            == "system-service"
        )
    )

    topology.graph.parents["app-1"] = [
        {
            "source": "system-service",
            "type": "HOSTED_ON",
            "confidence": 1.0,
            "evidence": [],
        },
        {
            "source": "vm-100",
            "type": "HOSTED_ON",
            "confidence": 1.0,
            "evidence": [],
        },
    ]

    with patch(
        "atlas.services.assets.topology_traversal.RelationshipType"
    ) as relationship_enum:

        relationship_enum.__getitem__.side_effect = (
            lambda name: name
        )

        with patch(
            "atlas.services.assets.topology_traversal.is_operational_relationship",
            return_value=True,
        ):

            with patch(
                "atlas.services.assets.topology_traversal.relationship_impact_score",
                return_value=10,
            ):

                result = topology.critical_upstream(
                    "app-1"
                )

    ids = {
        item["asset_id"]
        for item in result
    }

    assert (
        "system-service"
        not in ids
    )

    assert "vm-100" in ids


def test_critical_upstream_traverses_multiple_levels():

    topology = make_topology()

    topology.graph.parents["app-1"] = [
        {
            "source": "vm-100",
            "type": "HOSTED_ON",
            "confidence": 1.0,
            "evidence": ["VM"],
        }
    ]

    topology.graph.parents["vm-100"] = [
        {
            "source": "proxmox-1",
            "type": "HOSTED_ON",
            "confidence": 0.8,
            "evidence": ["hypervisor"],
        }
    ]

    with patch(
        "atlas.services.assets.topology_traversal.RelationshipType"
    ) as relationship_enum:

        relationship_enum.__getitem__.side_effect = (
            lambda name: name
        )

        with patch(
            "atlas.services.assets.topology_traversal.is_operational_relationship",
            return_value=True,
        ):

            with patch(
                "atlas.services.assets.topology_traversal.relationship_impact_score",
                return_value=10,
            ):

                result = topology.critical_upstream(
                    "app-1",
                    depth=5,
                )

    assert [
        item["asset_id"]
        for item in result
    ] == [
        "vm-100",
        "proxmox-1",
    ]

    assert result[0]["depth"] == 1
    assert result[1]["depth"] == 2

    assert result[0]["impact_score"] == 10.0
    assert result[1]["impact_score"] == 4.0


def test_critical_upstream_respects_depth():

    topology = make_topology()

    topology.graph.parents["app-1"] = [
        {
            "source": "vm-100",
            "type": "HOSTED_ON",
            "confidence": 1.0,
            "evidence": [],
        }
    ]

    topology.graph.parents["vm-100"] = [
        {
            "source": "proxmox-1",
            "type": "HOSTED_ON",
            "confidence": 1.0,
            "evidence": [],
        }
    ]

    with patch(
        "atlas.services.assets.topology_traversal.RelationshipType"
    ) as relationship_enum:

        relationship_enum.__getitem__.side_effect = (
            lambda name: name
        )

        with patch(
            "atlas.services.assets.topology_traversal.is_operational_relationship",
            return_value=True,
        ):

            result = topology.critical_upstream(
                "app-1",
                depth=1,
            )

    assert [
        item["asset_id"]
        for item in result
    ] == [
        "vm-100"
    ]


def test_critical_upstream_does_not_duplicate_cycles():

    topology = make_topology()

    topology.graph.parents["app-1"] = [
        {
            "source": "vm-100",
            "type": "HOSTED_ON",
            "confidence": 1.0,
            "evidence": [],
        }
    ]

    topology.graph.parents["vm-100"] = [
        {
            "source": "proxmox-1",
            "type": "HOSTED_ON",
            "confidence": 1.0,
            "evidence": [],
        }
    ]

    topology.graph.parents["proxmox-1"] = [
        {
            "source": "vm-100",
            "type": "HOSTED_ON",
            "confidence": 1.0,
            "evidence": [],
        }
    ]

    with patch(
        "atlas.services.assets.topology_traversal.RelationshipType"
    ) as relationship_enum:

        relationship_enum.__getitem__.side_effect = (
            lambda name: name
        )

        with patch(
            "atlas.services.assets.topology_traversal.is_operational_relationship",
            return_value=True,
        ):

            result = topology.critical_upstream(
                "app-1",
                depth=5,
            )

    ids = [
        item["asset_id"]
        for item in result
    ]

    assert ids == [
        "vm-100",
        "proxmox-1",
    ]

    assert len(ids) == len(set(ids))
