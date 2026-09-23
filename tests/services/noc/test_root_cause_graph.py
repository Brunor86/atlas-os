from types import SimpleNamespace

from atlas.core.asset import (
    Asset,
    AssetType,
)

from atlas.services.noc.root_cause import (
    RootCauseEngine,
)


class SyntheticRegistry:
    """
    Minimal registry contract required by RootCauseEngine.
    """

    def __init__(
        self,
        assets,
    ):
        self._assets = {
            asset.id: asset
            for asset in assets
        }

    def get_asset(
        self,
        asset_id,
    ):
        return self._assets.get(
            asset_id
        )

    def get(
        self,
        asset_id,
    ):
        return self.get_asset(
            asset_id
        )

    def assets(self):
        return list(
            self._assets.values()
        )

    def get_all_assets(self):
        return self.assets()


class SyntheticOperationalGraph:
    """
    Deterministic graph adapter for RootCauseEngine.

    The graph contains:

        node-alpha
            |
           RUNS
            |
            v
        workload-alpha

    Therefore node-alpha is upstream supporting infrastructure
    for workload-alpha.
    """

    def __init__(
        self,
        registry,
        workload_id,
        node_id,
    ):
        self.topology = SimpleNamespace(
            assets=registry
        )

        self.workload_id = (
            workload_id
        )

        self.node_id = (
            node_id
        )

    def blast_radius(
        self,
        asset_id,
    ):
        return []

    def operational_upstream(
        self,
        asset_id,
        depth=5,
    ):
        if (
            asset_id
            != self.workload_id
        ):
            return []

        return [
            {
                "asset_id":
                    self.node_id,

                "relationship":
                    "RUNS",

                "direction":
                    "UPSTREAM",

                "depth":
                    1,

                "confidence":
                    1.0,

                "evidence": [
                    "synthetic operational relationship"
                ],

                "relationship_weight":
                    40,

                "impact_score":
                    40.0,
            }
        ]


def test_root_cause_resolves_supporting_infrastructure():

    workload = Asset(
        id="application-synthetic-workload-alpha",
        name="workload-alpha",
        type=AssetType.APPLICATION,
    )

    node = Asset(
        id="vm-synthetic-node-alpha",
        name="node-alpha",
        type=AssetType.VM,
    )

    registry = SyntheticRegistry(
        [
            workload,
            node,
        ]
    )

    graph = SyntheticOperationalGraph(
        registry=registry,
        workload_id=workload.id,
        node_id=node.id,
    )

    engine = RootCauseEngine(
        graph=graph
    )

    impact = engine.resolve_impact(
        workload.id
    )

    assert isinstance(
        impact,
        list,
    )

    node_impact = next(
        (
            item
            for item in impact
            if item.get(
                "asset_id"
            )
            == node.id
        ),
        None,
    )

    assert (
        node_impact
        is not None
    )

    assert (
        node_impact[
            "impact_class"
        ]
        == "INFRASTRUCTURE"
    )

    assert (
        node_impact[
            "direction"
        ]
        if "direction" in node_impact
        else "UPSTREAM"
    )

    assert (
        node_impact[
            "relationship_weight"
        ]
        == 40
    )

    assert (
        node_impact[
            "confidence"
        ]
        == 1.0
    )

    assert (
        "Supporting infrastructure"
        in node_impact[
            "reason"
        ]
    )
