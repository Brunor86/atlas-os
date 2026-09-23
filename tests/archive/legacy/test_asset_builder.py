from atlas.collectors.smart import SmartCollector
from atlas.services.assets.builder import AssetBuilder
from atlas.core.asset import Capability


collector = SmartCollector("/dev/sda")

smart_list = collector.collect()

smart = smart_list[0]


builder = AssetBuilder()

asset = builder.from_smart(smart)


print(asset)

print()

print("Online:", asset.is_online())

print("Healthy:", asset.is_healthy())

print("SMART:", asset.can(Capability.SMART))
