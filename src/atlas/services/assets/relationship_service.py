from atlas.storage.graph_repository import GraphRepository


class AssetRelationshipService:


    def __init__(self):

        self.repository = GraphRepository()



    def add_relationship(
        self,
        source_asset,
        target_asset,
        relationship
    ):

        source_asset.add_relationship(
            relationship
        )

        self.repository.save_relationship(
            relationship
        )



    def get_outgoing(
        self,
        asset_id
    ):

        return self.repository.get_children(
            asset_id
        )



    def get_incoming(
        self,
        asset_id
    ):

        return self.repository.get_parents(
            asset_id
        )
