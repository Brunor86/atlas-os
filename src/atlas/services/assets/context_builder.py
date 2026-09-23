from atlas.models.asset_context import AssetContext

from atlas.services.assets.registry import AssetRegistry

from atlas.storage.graph_repository import GraphRepository



class AssetContextBuilder:


    def __init__(
        self,
        registry: AssetRegistry,
    ):

        self.registry = registry



    def build(
        self,
        asset_id: str,
    ) -> AssetContext | None:

        asset = self.registry.get(
            asset_id
        )

        if asset is None:
            return None


        graph = GraphRepository()


        return AssetContext(

            id=asset.id,

            name=asset.name,

            type=asset.type.name,

            status=asset.status.name,

            criticality=(
                asset.criticality.name
            ),

            roles=[
                role.name
                for role
                in asset.asset_roles
            ],

            weight=(
                asset.role_weight()
            ),

            capabilities=[
                capability.name
                for capability
                in asset.capabilities
            ],

            parents=graph.get_parents(
                asset.id
            ),

            children=graph.get_children(
                asset.id
            ),

            impact_path=[],

        )
