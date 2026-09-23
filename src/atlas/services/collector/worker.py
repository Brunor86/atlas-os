import time
import logging

from atlas.services.collector.operational_cycle import (
    OperationalCycleService,
)

from atlas.services.control_plane.cycle_status import (
    OperationalCycleStatusStore,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)


class CollectorWorker:

    def __init__(
        self,
        interval=300,
        cycle=None,
        status_store=None,
    ):

        self.interval = interval

        self.cycle = (
            cycle
            or OperationalCycleService()
        )

        self.status_store = (
            status_store
            or OperationalCycleStatusStore()
        )

        #
        # Historical compatibility for callers that inspect
        # worker.collector.
        #
        self.collector = (
            self.cycle
        )


    def _record_status(
        self,
        method,
        *args,
    ):
        """
        Control-plane observability must never become a new
        failure mode for the authoritative operational cycle.
        """

        try:

            callback = getattr(
                self.status_store,
                method,
            )

            callback(
                *args
            )

        except Exception as exc:

            logging.exception(
                (
                    "Operational cycle status "
                    "persistence error phase=%s: %s"
                ),
                method,
                exc,
            )


    def collect_once(
        self,
    ):

        self._record_status(
            "mark_started"
        )

        logging.info(
            "Starting ATLAS operational cycle"
        )

        try:

            result = (
                self.cycle.run_once()
            )

            discovery = (
                result.get(
                    "discovery"
                )
                if isinstance(
                    result,
                    dict,
                )
                else None
            )

            reconciliation = (
                result.get(
                    "reconciliation"
                )
                if isinstance(
                    result,
                    dict,
                )
                else None
            )

            discovery_count = getattr(
                discovery,
                "count",
                None,
            )

            discovery_complete = getattr(
                discovery,
                "complete",
                None,
            )

            if (
                discovery is not None
                and discovery_complete
                is False
            ):

                logging.warning(
                    (
                        "ATLAS discovery degraded "
                        "assets=%s errors=%s"
                    ),
                    discovery_count,
                    getattr(
                        discovery,
                        "errors",
                        [],
                    ),
                )

            presence_counts = {}

            transitions = 0

            if isinstance(
                reconciliation,
                dict,
            ):

                presence_counts = (
                    reconciliation.get(
                        "counts",
                        {}
                    )
                    or {}
                )

                transitions = len(
                    reconciliation.get(
                        "transitions",
                        []
                    )
                    or []
                )

            logging.info(
                (
                    "ATLAS operational cycle completed successfully "
                    "discovery_assets=%s "
                    "discovery_complete=%s "
                    "active=%s "
                    "stale=%s "
                    "retired=%s "
                    "transitions=%s"
                ),
                discovery_count,
                discovery_complete,
                presence_counts.get(
                    "ACTIVE"
                ),
                presence_counts.get(
                    "STALE"
                ),
                presence_counts.get(
                    "RETIRED"
                ),
                transitions,
            )

        except Exception as exc:

            self._record_status(
                "mark_failed",
                exc,
            )

            raise

        self._record_status(
            "mark_success",
            result,
        )

        return result


    def run(
        self,
    ):

        logging.info(
            "ATLAS Collector started"
        )

        while True:

            try:

                self.collect_once()

            except Exception as exc:

                logging.exception(
                    "Operational cycle error: %s",
                    exc,
                )

            #
            # Single-threaded worker:
            # one cycle must finish before the next one begins.
            #
            time.sleep(
                self.interval
            )


if __name__ == "__main__":

    worker = CollectorWorker()

    worker.run()
