from atlas.agent.runner import AgentRunner
from atlas.collectors.smart import SmartCollector
from atlas.storage.asset_repository import AssetRepository


agent = AgentRunner(
    "proxmox-atlas",
    "atlas"
)


agent.add_collector(
    SmartCollector("/dev/sda")
)


report = agent.discover()


repo = AssetRepository()


for asset in report.assets:

    repo.save_asset(asset)

    for obs in asset.observations:

        repo.save_observation(obs)


print("Guardado OK")
