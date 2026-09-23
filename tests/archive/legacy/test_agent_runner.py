from atlas.agent.runner import AgentRunner
from atlas.collectors.smart import SmartCollector


agent = AgentRunner()


agent.add_collector(
    SmartCollector("/dev/sda")
)


results = agent.collect()


print("Reporte del agente")
print()


for item in results:
    print(item)
