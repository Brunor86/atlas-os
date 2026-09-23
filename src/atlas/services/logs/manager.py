from atlas.services.logs.docker import (
    DockerLogCollector,
)
from atlas.services.logs.analyzer import (
    LogAnalyzer,
)

from atlas.services.assets.criticality import (
    parse_criticality,
)

from atlas.core.asset import Criticality


class LogManager:

    def __init__(
        self,
    ):

        self.collector = (
            DockerLogCollector()
        )

        self.analyzer = (
            LogAnalyzer()
        )

    def analyze_containers(
        self,
        containers,
    ):

        results = []

        for container in containers:

            name = container.get(
                "name"
            )

            status = container.get(
                "status"
            )

            criticality = (
                parse_criticality(
                    container.get(
                        "criticality"
                    )
                )
            )

            critical = (
                criticality
                == Criticality.CRITICAL
            )

            proactive_analysis = (
                criticality
                in {
                    Criticality.HIGH,
                    Criticality.CRITICAL,
                }
            )

            if (
                status != "running"
                or proactive_analysis
            ):

                logs = (
                    self.collector.get_logs(
                        name,
                        100,
                    )
                )

                analysis = (
                    self.analyzer.analyze(
                        logs,
                        container,
                    )
                )

                results.append(
                    {
                        "container":
                            name,

                        "status":
                            status,

                        "criticality":
                            criticality.name,

                        "critical":
                            critical,

                        "analysis":
                            analysis,
                    }
                )

        return results
