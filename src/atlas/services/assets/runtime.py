from atlas.services.assets.registry import AssetRegistry


_registry = None


def get_asset_registry():

    global _registry

    if _registry is None:

        _registry = AssetRegistry()

        _registry.load_persisted()

    return _registry


class AssetRuntimeService:

    def __init__(self):

        self.registry = get_asset_registry()


    def assets(self):

        return self.registry.assets()


    def get(self, asset_id):

        return self.registry.get(
            asset_id
        )


    def discover(self):

        self.registry.discover()

        return self.registry.assets()
