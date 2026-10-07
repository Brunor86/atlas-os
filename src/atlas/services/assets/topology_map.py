from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from atlas.storage.asset_repository import (
    AssetRepository,
)
from atlas.storage.graph_repository import (
    GraphRepository,
)


_NETWORK_METADATA_KEYS = (
    "hostname",
    "host",
    "ip",
    "ip_address",
    "mac",
    "mac_address",
    "interface",
    "bridge",
    "network",
    "vmid",
)


class TopologyMapService:
    """
    Read-only topology snapshot for ATLAS Map.

    AssetRepository is authoritative for active inventory.
    GraphRepository is authoritative for persisted relationships.

    The service never infers missing topology and never mutates
    infrastructure or graph state.
    """

    def __init__(
        self,
        asset_repository=None,
        graph_repository=None,
    ):
        self.assets = (
            asset_repository
            or AssetRepository()
        )

        self.graph = (
            graph_repository
            or GraphRepository()
        )


    def snapshot(
        self,
    ):
        assets = (
            self.assets
            .get_active_assets()
        )

        active_ids = {
            asset.id
            for asset in assets
        }

        relationships = [
            relationship
            for relationship
            in self.graph.list_relationships()
            if (
                relationship["source"]
                in active_ids
                and relationship["target"]
                in active_ids
            )
        ]


        connected = set()

        incoming_hosts = Counter()

        for relationship in relationships:

            connected.add(
                relationship["source"]
            )

            connected.add(
                relationship["target"]
            )

            if (
                relationship["type"]
                == "HOSTS"
            ):
                incoming_hosts[
                    relationship["target"]
                ] += 1


        nodes = [
            self._node(
                asset,
                connected=(
                    asset.id
                    in connected
                ),
            )
            for asset in assets
        ]

        nodes.sort(
            key=lambda node: (
                node["type"],
                node["name"].lower(),
                node["id"],
            )
        )


        edges = [
            {
                "source":
                    relationship["source"],

                "target":
                    relationship["target"],

                "type":
                    relationship["type"],

                "confidence":
                    relationship["confidence"],

                "evidence":
                    list(
                        relationship.get(
                            "evidence",
                            [],
                        )
                        or []
                    ),

                "metadata":
                    dict(
                        relationship.get(
                            "metadata",
                            {},
                        )
                        or {}
                    ),
            }
            for relationship
            in relationships
        ]


        by_type = Counter(
            node["type"]
            for node in nodes
        )

        by_status = Counter(
            node["status"]
            for node in nodes
        )

        by_relationship = Counter(
            edge["type"]
            for edge in edges
        )


        root_ids = [
            node["id"]
            for node in nodes
            if incoming_hosts[
                node["id"]
            ] == 0
        ]


        return {
            "status":
                "SUCCESS",

            "generated_at":
                datetime.now(
                    UTC
                ).isoformat(),

            "summary": {
                "nodes":
                    len(nodes),

                "edges":
                    len(edges),

                "connected_nodes":
                    len(connected),

                "unconnected_nodes":
                    (
                        len(nodes)
                        - len(connected)
                    ),

                "root_nodes":
                    len(root_ids),

                "by_type":
                    dict(
                        sorted(
                            by_type.items()
                        )
                    ),

                "by_status":
                    dict(
                        sorted(
                            by_status.items()
                        )
                    ),

                "by_relationship":
                    dict(
                        sorted(
                            by_relationship.items()
                        )
                    ),
            },

            "root_ids":
                root_ids,

            "nodes":
                nodes,

            "edges":
                edges,
        }


    def _node(
        self,
        asset,
        *,
        connected,
    ):
        metadata = (
            asset.metadata
            or {}
        )

        network = {
            key: metadata[key]
            for key in _NETWORK_METADATA_KEYS
            if (
                key in metadata
                and metadata[key]
                is not None
            )
        }


        return {
            "id":
                asset.id,

            "name":
                asset.name,

            "type":
                asset.type.name,

            "status":
                asset.status.name,

            "health":
                float(
                    asset.health
                    or 0.0
                ),

            "criticality":
                asset.criticality.name,

            "presence":
                asset.presence.name,

            "last_seen":
                asset.last_seen.isoformat(),

            "roles":
                sorted(
                    role.name
                    for role
                    in asset.asset_roles
                ),

            "primary_role":
                asset.primary_role.name,

            "connected":
                bool(
                    connected
                ),

            "network":
                network,

            "identity": {
                "serial":
                    asset.identity.serial,

                "model":
                    asset.identity.model,

                "vendor":
                    asset.identity.vendor,

                "device":
                    asset.identity.device,
            },
        }
