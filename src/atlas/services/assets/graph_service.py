from atlas.storage.graph_repository import GraphRepository


class AssetGraphService:

    def __init__(self):
        self.repository = GraphRepository()

    def persist(self, relationships):
        """
        Rebuild graph from current discovery state.
        """

        self.repository.clear_relationships()

        for relationship in relationships:
            self.repository.save_relationship(
                relationship
            )

    def parents(self, asset_id):
        """
        Return direct upstream relationships.
        """
        return self.repository.get_parents(
            asset_id
        )

    def children(self, asset_id):
        """
        Return direct downstream relationships.
        """
        return self.repository.get_children(
            asset_id
        )

    def neighbors(self, asset_id):
        """
        Return direct upstream and downstream relationships.
        """
        return self.repository.get_neighbors(
            asset_id
        )

    def impact_tree(
        self,
        asset_id,
        max_depth=3,
    ):
        """
        Return downstream impact tree.
        """
        return self.repository.get_impact_tree(
            asset_id,
            max_depth=max_depth,
        )

    def critical_upstream(self, asset_id):
        """
        Return complete upstream dependency chain.
        """
        return self.repository.get_critical_upstream(
            asset_id
        )

    def operational_upstream(self, asset_id):
        """
        Return operationally relevant upstream assets.
        """
        return self.repository.get_operational_upstream(
            asset_id
        )
