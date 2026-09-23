from atlas.services.logs.manager import (
    LogManager,
)


class FakeCollector:

    def __init__(self):

        self.calls = []

    def get_logs(
        self,
        name,
        lines,
    ):

        self.calls.append(
            (
                name,
                lines,
            )
        )

        return [
            "example log"
        ]


class FakeAnalyzer:

    def analyze(
        self,
        logs,
        container,
    ):

        return {
            "pattern":
                "test",
            "severity":
                "LOW",
        }


def manager():

    instance = LogManager()

    instance.collector = (
        FakeCollector()
    )

    instance.analyzer = (
        FakeAnalyzer()
    )

    return instance


def test_running_medium_container_is_not_analyzed():

    instance = manager()

    result = (
        instance.analyze_containers(
            [
                {
                    "name":
                        "generic-workload",

                    "status":
                        "running",

                    "criticality":
                        "MEDIUM",
                }
            ]
        )
    )

    assert result == []

    assert (
        instance.collector.calls
        == []
    )


def test_running_high_container_is_analyzed():

    instance = manager()

    result = (
        instance.analyze_containers(
            [
                {
                    "name":
                        "generic-workload",

                    "status":
                        "running",

                    "criticality":
                        "HIGH",
                }
            ]
        )
    )

    assert len(result) == 1

    assert (
        result[0]["criticality"]
        == "HIGH"
    )

    assert (
        result[0]["critical"]
        is False
    )


def test_running_critical_container_is_analyzed():

    instance = manager()

    result = (
        instance.analyze_containers(
            [
                {
                    "name":
                        "generic-workload",

                    "status":
                        "running",

                    "criticality":
                        "CRITICAL",
                }
            ]
        )
    )

    assert len(result) == 1

    assert (
        result[0]["criticality"]
        == "CRITICAL"
    )

    assert (
        result[0]["critical"]
        is True
    )


def test_stopped_medium_container_is_always_analyzed():

    instance = manager()

    result = (
        instance.analyze_containers(
            [
                {
                    "name":
                        "generic-workload",

                    "status":
                        "exited",

                    "criticality":
                        "MEDIUM",
                }
            ]
        )
    )

    assert len(result) == 1

    assert (
        result[0]["criticality"]
        == "MEDIUM"
    )
