
from atlas.storage.asset_repository import AssetRepository
from atlas.storage.graph_repository import GraphRepository

from atlas.services.assets.topology_traversal import (
    TopologyTraversalService,
)


class ImpactEngine:

    def __init__(self):
        self.assets = AssetRepository()
        self.graph = GraphRepository()
        self.topology = TopologyTraversalService()

    def rank_root_causes(
        self,
        upstream,
    ):
        candidates = []

        for item in upstream:

            asset_id = (
                item.get("asset_id")
                or item.get("source")
            )

            relationship = (
                item.get("relationship")
                or item.get("type")
            )

            depth = item.get(
                "depth",
                1,
            )

            confidence = float(
                item.get(
                    "confidence",
                    0.0,
                )
                or 0.0
            )

            relationship_weight = item.get(
                "relationship_weight",
                item.get(
                    "weight",
                    0,
                ),
            )

            root_score = float(
                item.get(
                    "impact_score",
                    0.0,
                )
                or 0.0
            )

            candidates.append(
                {
                    "asset_id": asset_id,
                    "relationship": relationship,
                    "depth": depth,
                    "confidence": confidence,
                    "relationship_weight": (
                        relationship_weight
                    ),
                    "root_score": round(
                        root_score,
                        2,
                    ),
                    "evidence": item.get(
                        "evidence",
                        [],
                    ),
                }
            )

        return sorted(
            candidates,
            key=lambda item: item["root_score"],
            reverse=True,
        )

    def analyze(
        self,
        asset_id,
    ):

        asset = self.assets.get_asset(
            asset_id
        )

        if not asset:
            return {
                "error": "asset not found"
            }

        upstream = (
            self.topology.critical_upstream(
                asset_id
            )
        )

        downstream = (
            self.topology.downstream(
                asset_id
            )
        )

        criticality_score = {
            "LOW": 10,
            "MEDIUM": 30,
            "HIGH": 70,
            "CRITICAL": 100,
        }

        score = criticality_score.get(
            asset.criticality.name,
            0,
        )

        # IMPORTANT:
        #
        # Upstream infrastructure is used for root-cause analysis.
        # It must NOT automatically increase the incident impact score.
        #
        # Example:
        #
        #     Proxmox
        #        |
        #       VM 100
        #        |
        #       NPM OFFLINE
        #
        # The VM and Proxmox are dependencies of NPM, not downstream
        # victims of the NPM incident.
        #
        # Therefore upstream impact is intentionally excluded here.
        #
        score += len(downstream) * 10

        role_weights = {
            "DATABASE_SERVER": 40,
            "HYPERVISOR": 40,
            "STORAGE": 40,
            "NETWORK": 40,
            "APPLICATION_SERVER": 30,
            "MEDIA_SERVER": 20,
            "MONITORING_NODE": 20,
            "UTILITY_SERVICE": 10,
        }

        for role in asset.asset_roles:
            score += role_weights.get(
                role.name,
                0,
            )

        if score >= 100:
            severity = "CRITICAL"
        elif score >= 60:
            severity = "HIGH"
        elif score >= 30:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        root_causes = self.rank_root_causes(
            upstream
        )

        return {
            "asset": asset.id,
            "name": asset.name,
            "criticality": asset.criticality.name,
            "roles": [
                role.name
                for role in asset.asset_roles
            ],
            "impact_score": round(
                score,
                2,
            ),
            "severity": severity,
            "operational_upstream": upstream,
            "root_causes": root_causes,
            "downstream": downstream,
        }
