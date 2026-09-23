import logging


class FailingPrometheus:

    def query(
        self,
        expression,
    ):

        raise RuntimeError(
            "synthetic Prometheus outage"
        )


class HealthyPrometheus:

    def query(
        self,
        expression,
    ):

        if (
            expression
            == "container_memory_usage_bytes"
        ):

            return [
                {
                    "metric": {
                        "name":
                            "example-container",

                        "image":
                            "example:latest",
                    },

                    "value": [
                        0,
                        str(
                            128
                            * 1024
                            * 1024
                        ),
                    ],
                },
            ]

        if (
            expression
            == "rate(container_cpu_usage_seconds_total[5m])"
        ):

            return [
                {
                    "metric": {
                        "name":
                            "example-container",
                    },

                    "value": [
                        0,
                        "0.125",
                    ],
                },
            ]

        return []


def test_docker_memory_survives_prometheus_outage(
    caplog,
):

    from atlas.services.metrics.service import (
        MetricsService,
    )


    service = MetricsService(
        prometheus=FailingPrometheus()
    )


    with caplog.at_level(
        logging.WARNING
    ):

        result = (
            service.docker_memory()
        )


    assert result == {}

    assert (
        "Prometheus metrics unavailable"
        in caplog.text
    )


def test_docker_cpu_survives_prometheus_outage(
    caplog,
):

    from atlas.services.metrics.service import (
        MetricsService,
    )


    service = MetricsService(
        prometheus=FailingPrometheus()
    )


    with caplog.at_level(
        logging.WARNING
    ):

        result = (
            service.docker_cpu()
        )


    assert result == {}

    assert (
        "Prometheus metrics unavailable"
        in caplog.text
    )


def test_prometheus_metrics_still_enrich_when_available():

    from atlas.services.metrics.service import (
        MetricsService,
    )


    service = MetricsService(
        prometheus=HealthyPrometheus()
    )


    memory = service.docker_memory()
    cpu = service.docker_cpu()


    assert memory == {
        "example-container": {
            "memory_mb": 128.0,
            "image": "example:latest",
        },
    }

    assert cpu == {
        "example-container": {
            "cpu_percent": 12.5,
        },
    }
