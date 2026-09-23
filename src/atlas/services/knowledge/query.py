from atlas.services.knowledge.graph import GraphService
from atlas.services.assets.runtime import get_asset_registry

class KnowledgeQueryService:
    """
    Read-only query layer over ATLAS knowledge.

    Provides semantic queries over assets,
    dependencies, dependents and topology.
    """

    def __init__(self, knowledge_service):

        self.knowledge = knowledge_service

        self.registry = getattr(
            knowledge_service,
            "registry",
            None,
        )

        if self.registry is None:
            self.registry = get_asset_registry()

        self.graph = GraphService(
            self.registry
        )


    def list_cards(self):

        return self.knowledge.cards

    def get_card(
        self,
        asset_id: str,
    ):

        for card in self.knowledge.cards:

            if card.asset_id == asset_id:
                return card

        return None

    def dependencies(
        self,
        asset_id: str,
    ):

        """
        Returns what an asset depends on.
        """

        return self.graph.get_dependencies(
            asset_id
        )

    def dependents(
        self,
        asset_id: str,
    ):

        """
        Returns assets that depend on this asset.

        These are the assets potentially impacted
        if this asset fails.
        """

        return self.graph.get_dependents(
            asset_id
        )

    def neighbors(
        self,
        asset_id: str,
    ):

        return self.graph.get_neighbors(
            asset_id
        )

    def impact_path(
        self,
        asset_id: str,
        depth: int = 3,
    ):

        return self.graph.impact_analysis(
            asset_id,
            depth,
        )

    def asset_context(
        self,
        asset_id: str,
    ):

        card = self.get_card(
            asset_id
        )

        if not card:
            return None

        return {
            "asset_id":
                card.asset_id,

            "name":
                card.asset_name,

            "type":
                card.asset_type,

            "dependencies":
                card.dependencies,

            "dependents":
                card.dependents,
        }
