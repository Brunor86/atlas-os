from atlas.core.provider import AssetProvider
from atlas.storage.asset_repository import AssetRepository


class RepositoryAssetProvider(AssetProvider):

    def __init__(self):
        self.repository = AssetRepository()


    def collect(self):

        from atlas.core.asset import AssetType

        assets = self.repository.get_all_assets()

        return [
            asset
            for asset in assets
            if asset.type != AssetType.STORAGE
        ]
