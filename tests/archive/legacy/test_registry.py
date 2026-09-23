from atlas.core.asset import Asset, AssetType, AssetStatus
from atlas.services.assets.registry import AssetRegistry

registry = AssetRegistry()

disk = Asset(
    id="disk01",
    name="WD Red Pro",
    type=AssetType.STORAGE,
    status=AssetStatus.ONLINE,
)

container = Asset(
    id="docker-jellyfin",
    name="Jellyfin",
    type=AssetType.CONTAINER,
    status=AssetStatus.ONLINE,
)

registry.register(disk)
registry.register(container)

print("Total:", registry.count())

print()

print("Todos los Assets")
for asset in registry.all():
    print("-", asset.name)

print()

print("Containers")
for asset in registry.by_type(AssetType.CONTAINER):
    print("-", asset.name)
