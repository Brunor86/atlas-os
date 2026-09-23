import logging

from atlas.services.metrics.prometheus import PrometheusClient


logger = logging.getLogger(__name__)


class MetricsService:


    def __init__(
        self,
        prometheus=None,
    ):

        self.prometheus = (
            prometheus
            if prometheus is not None
            else PrometheusClient()
        )


    def _query(
        self,
        expression,
    ):
        """
        Query optional Prometheus metrics.

        Prometheus enriches the dashboard with container CPU and memory
        telemetry, but it is not required for ATLAS core operation.

        A missing or unavailable Prometheus endpoint therefore produces
        no enrichment instead of making the dashboard unavailable.
        """

        try:

            return self.prometheus.query(
                expression
            )

        except Exception as exc:

            logger.warning(
                "Prometheus metrics unavailable "
                "for %s: %s",
                expression,
                exc,
            )

            return []



    def _container_name(self, metric):

        return (
            metric.get("name")
            or metric.get("container_label_com_docker_compose_service")
            or metric.get("container_label_com_docker_compose_container_number")
            or metric.get("image")
            or "unknown"
        )



    def docker_memory(self):

        result = self._query(
            "container_memory_usage_bytes"
        )

        metrics = {}


        for item in result:

            metric = item.get(
                "metric",
                {}
            )


            name = self._container_name(
                metric
            )


            value = float(
                item["value"][1]
            )


            metrics[name] = {

                "memory_mb":
                    round(
                        value / 1024 / 1024,
                        1
                    ),

                "image":
                    metric.get(
                        "image",
                        ""
                    )

            }


        return metrics



    def docker_cpu(self):

        result = self._query(
            "rate(container_cpu_usage_seconds_total[5m])"
        )


        metrics = {}


        for item in result:

            metric = item.get(
                "metric",
                {}
            )


            name = self._container_name(
                metric
            )


            value = float(
                item["value"][1]
            )


            metrics[name] = {

                "cpu_percent":
                    round(
                        value * 100,
                        2
                    )

            }


        return metrics
