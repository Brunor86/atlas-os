from atlas.collectors.smart import SmartCollector

collector = SmartCollector()

info = collector.collect("/dev/sda")

print()

print(info)
