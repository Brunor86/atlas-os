from atlas.models.asset_context import AssetContext

from atlas.services.assets.context_builder import (
    AssetContextBuilder,
)



class AssetContextService:


    def __init__(
        self,
        builder: AssetContextBuilder,
    ):

        self.builder = builder



    def get(
        self,
        asset_id: str,
    ) -> AssetContext | None:

        return self.builder.build(
            asset_id
        )
