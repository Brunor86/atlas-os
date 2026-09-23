from atlas.collectors.base import Collector


class CollectorRegistry:

    def __init__(self):
        self.collectors: list[Collector] = []

    def register(self, collector: Collector):
        self.collectors.append(collector)

    def collect_all(self):
        results = []

        for collector in self.collectors:
            results.extend(
                collector.collect()
            )

        return results
