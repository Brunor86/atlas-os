from atlas.collectors.smart import SmartCollector
from atlas.services.assets.builder import AssetBuilder
from atlas.services.observations.smart import SmartObservationBuilder


collector = SmartCollector("/dev/sda")

smart = collector.collect()[0]


asset = AssetBuilder().from_smart(smart)


observations = SmartObservationBuilder().build(
    asset.id,
    smart
)


for obs in observations:
    asset.add_observation(obs)


print(asset)

print()

print("Observations:")

for obs in asset.observations:
    print(
        obs.asset_id,
        obs.type,
        obs.value,
        obs.severity
    )
