from atlas.agent.runner import AgentRunner
from atlas.collectors.smart import SmartCollector


agent = AgentRunner(
    "proxmox-atlas",
    "atlas"
)


agent.add_collector(
    SmartCollector("/dev/sda")
)


report = agent.discover()


print(report)


print()

print("Assets:")

for asset in report.assets:

    print(
        asset.name,
        asset.id
    )

    for obs in asset.observations:

        print(
            " ",
            obs.type,
            obs.value,
            obs.severity
        )
