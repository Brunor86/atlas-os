from atlas.core.asset import Asset
from atlas.core.provider import AssetProvider


class AssetRegistry:

    def __init__(self):

        self._providers: list[AssetProvider] = []

        self._assets: dict[str, Asset] = {}


    def register_provider(
        self,
        provider: AssetProvider
    ):

        self._providers.append(
            provider
        )


    def register(
        self,
        asset: Asset
    ):

        self._assets[
            asset.id
        ] = asset


    def discover(self):

        for provider in self._providers:

            assets = provider.collect()

            for asset in assets:

                self.register(
                    asset
                )


    def load_persisted(self):

        """
        Hydrate the runtime registry from persisted assets.

        SQLite is the persistent source of truth.
        AssetRegistry is the runtime source of truth.
        """

        from atlas.storage.asset_repository import AssetRepository

        repository = AssetRepository()

        #
        # Runtime operational registries contain only assets that
        # are currently confirmed by authoritative Discovery.
        #
        # STALE and RETIRED records remain available in SQLite for
        # history/audit but must not become operational targets.
        #
        assets = repository.get_active_assets()

        for asset in assets:

            self.register(
                asset
            )


    def assets(self):

        return list(
            self._assets.values()
        )


    def get(
        self,
        asset_id: str
    ):

        return self._assets.get(
            asset_id
        )


    def clear(self):

        self._assets.clear()


    def count(self):

        return len(
            self._assets
        )
