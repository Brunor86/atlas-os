from atlas.storage.graph_repository import GraphRepository
from atlas.services.knowledge.asset_resolver import AssetResolver


class GraphService:
    """
    Compatibility facade for graph operations.

    GraphRepository:
        owns graph persistence.

    TopologyTraversalService:
        owns traversal and topology semantics.

    AssetResolver:
        resolves logical/runtime asset identities.

    AssetGraphService:
        exposes operational upstream traversal backed by
        the persisted asset graph.

    GraphService intentionally acts as a compatibility facade
    and does not implement traversal semantics itself.
    """

    def __init__(self, registry=None):
        self.registry = registry

        self.repository = GraphRepository()

        self.resolver = AssetResolver(
            registry
        )

        from atlas.services.assets.topology_traversal import (
            TopologyTraversalService,
        )

        self.topology = TopologyTraversalService(
            registry=registry,
        )

    def _ensure_resolver(self):
        if self.resolver is None:
            self.resolver = AssetResolver(
                self.registry
            )

    # -----------------------------------------------------
    # DIRECT TOPOLOGY API
    # -----------------------------------------------------

    def get_dependencies(
        self,
        asset_id,
    ):
        return self.topology.get_dependencies(
            asset_id
        )

    def get_dependents(
        self,
        asset_id,
    ):
        return self.topology.get_dependents(
            asset_id
        )

    def get_neighbors(
        self,
        asset_id,
    ):
        return self.topology.get_neighbors(
            asset_id
        )

    # -----------------------------------------------------
    # TRAVERSAL API
    # -----------------------------------------------------

    def upstream(
        self,
        asset_id,
        depth=5,
    ):
        return self.topology.upstream(
            asset_id,
            depth=depth,
        )

    def downstream(
        self,
        asset_id,
        depth=5,
    ):
        return self.topology.downstream(
            asset_id,
            depth=depth,
        )

    def critical_upstream(
        self,
        asset_id,
        depth=5,
    ):
        return self.topology.critical_upstream(
            asset_id,
            depth=depth,
        )

    def operational_upstream(
        self,
        asset_id,
        depth=5,
    ):
        return self.topology.operational_upstream(
            asset_id,
            depth=depth,
        )

    def blast_radius(
        self,
        asset_id,
        depth=5,
    ):
        return self.topology.blast_radius(
            asset_id,
            depth=depth,
        )

    def impact_analysis(
        self,
        asset_id,
        depth=5,
    ):
        """
        Compatibility API.

        Historical callers use GraphService.impact_analysis().
        Traversal semantics live in TopologyTraversalService.
        """

        return self.topology.impact_analysis(
            asset_id,
            depth=depth,
        )

    # -----------------------------------------------------
    # REPOSITORY COMPATIBILITY
    # -----------------------------------------------------

    def get_parents(
        self,
        asset_id,
    ):
        return self.repository.get_parents(
            asset_id
        )

    def get_children(
        self,
        asset_id,
    ):
        return self.repository.get_children(
            asset_id
        )

    def get_neighbors_persisted(
        self,
        asset_id,
    ):
        return self.repository.get_neighbors(
            asset_id
        )
