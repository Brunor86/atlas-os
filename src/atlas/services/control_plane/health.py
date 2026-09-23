import sqlite3

from datetime import (
    UTC,
    datetime,
)

from pathlib import Path

from atlas.services.ai.runtime_status import (
    AIRuntimeStatusService,
)

from atlas.services.control_plane.cycle_status import (
    OperationalCycleStatusStore,
)

from atlas.storage.database import (
    configured_database_path,
)


HEALTHY_CYCLE_AGE_SECONDS = 600
DEGRADED_CYCLE_AGE_SECONDS = 900
MAX_RUNNING_AGE_SECONDS = 120


class ControlPlaneHealthService:
    """
    Deterministic health view of the ATLAS control plane.

    This intentionally does not answer whether the managed
    infrastructure is healthy. It answers whether ATLAS itself
    is operating correctly and has recent authoritative state.
    """

    def __init__(
        self,
        status_store=None,
        ai_status=None,
        database_path: str | Path | None = None,
        clock=None,
    ):

        self.database_path = (
            Path(database_path)
            if database_path is not None
            else configured_database_path()
        )

        self.status_store = (
            status_store
            or OperationalCycleStatusStore(
                self.database_path
            )
        )

        self.ai_status = (
            ai_status
            or AIRuntimeStatusService()
        )

        self.clock = (
            clock
            or (
                lambda:
                    datetime.now(
                        UTC
                    )
            )
        )


    @staticmethod
    def _parse_timestamp(
        value,
    ):

        if not value:
            return None

        parsed = datetime.fromisoformat(
            value
        )

        if parsed.tzinfo is None:

            parsed = parsed.replace(
                tzinfo=UTC
            )

        return parsed


    def _age_seconds(
        self,
        value,
    ):

        parsed = self._parse_timestamp(
            value
        )

        if parsed is None:
            return None

        age = (
            self.clock()
            - parsed
        ).total_seconds()

        return max(
            0,
            int(age),
        )


    def _database_component(
        self,
    ):

        path = Path(
            self.database_path
        )

        if not path.exists():

            return {
                "status":
                    "UNHEALTHY",

                "reason":
                    "DATABASE_NOT_FOUND",

                "path":
                    str(path),
            }

        resolved = path.resolve()

        try:

            connection = sqlite3.connect(
                f"file:{resolved}?mode=ro",
                uri=True,
                timeout=5,
            )

            try:

                value = connection.execute(
                    "SELECT 1"
                ).fetchone()

            finally:
                connection.close()

        except Exception as exc:

            return {
                "status":
                    "UNHEALTHY",

                "reason":
                    "DATABASE_QUERY_FAILED",

                "error":
                    str(exc),
            }

        if (
            not value
            or value[0] != 1
        ):

            return {
                "status":
                    "UNHEALTHY",

                "reason":
                    "DATABASE_QUERY_INVALID",
            }

        return {
            "status":
                "HEALTHY",

            "reason":
                "DATABASE_READABLE",
        }


    def _collector_component(
        self,
        cycle,
    ):

        if cycle is None:

            return {
                "status":
                    "UNHEALTHY",

                "reason":
                    "NO_CYCLE_STATUS",

                "state":
                    "UNKNOWN",

                "last_success_at":
                    None,

                "age_seconds":
                    None,
            }

        state = str(
            cycle.get(
                "state",
                "UNKNOWN",
            )
            or "UNKNOWN"
        ).upper()

        last_success = cycle.get(
            "last_success_at"
        )

        success_age = (
            self._age_seconds(
                last_success
            )
        )

        if state == "FAILED":

            return {
                "status":
                    "UNHEALTHY",

                "reason":
                    "LAST_CYCLE_FAILED",

                "state":
                    state,

                "last_success_at":
                    last_success,

                "age_seconds":
                    success_age,

                "error":
                    cycle.get(
                        "last_error"
                    ),
            }

        if state == "RUNNING":

            running_age = (
                self._age_seconds(
                    cycle.get(
                        "started_at"
                    )
                )
            )

            if (
                running_age is not None
                and running_age
                > MAX_RUNNING_AGE_SECONDS
            ):

                return {
                    "status":
                        "UNHEALTHY",

                    "reason":
                        "CYCLE_RUNNING_TOO_LONG",

                    "state":
                        state,

                    "running_seconds":
                        running_age,

                    "last_success_at":
                        last_success,

                    "age_seconds":
                        success_age,
                }

            if last_success is None:

                return {
                    "status":
                        "DEGRADED",

                    "reason":
                        "FIRST_CYCLE_RUNNING",

                    "state":
                        state,

                    "running_seconds":
                        running_age,

                    "last_success_at":
                        None,

                    "age_seconds":
                        None,
                }

        if success_age is None:

            return {
                "status":
                    "UNHEALTHY",

                "reason":
                    "NO_SUCCESSFUL_CYCLE",

                "state":
                    state,

                "last_success_at":
                    last_success,

                "age_seconds":
                    None,
            }

        if (
            success_age
            <= HEALTHY_CYCLE_AGE_SECONDS
        ):

            return {
                "status":
                    "HEALTHY",

                "reason":
                    (
                        "CYCLE_RUNNING"
                        if state == "RUNNING"
                        else "CYCLE_FRESH"
                    ),

                "state":
                    state,

                "last_success_at":
                    last_success,

                "age_seconds":
                    success_age,
            }

        if (
            success_age
            <= DEGRADED_CYCLE_AGE_SECONDS
        ):

            return {
                "status":
                    "DEGRADED",

                "reason":
                    "CYCLE_STALE",

                "state":
                    state,

                "last_success_at":
                    last_success,

                "age_seconds":
                    success_age,
            }

        return {
            "status":
                "UNHEALTHY",

            "reason":
                "CYCLE_EXPIRED",

            "state":
                state,

            "last_success_at":
                last_success,

            "age_seconds":
                success_age,
        }


    @staticmethod
    def _discovery_component(
        cycle,
    ):

        if cycle is None:

            return {
                "status":
                    "UNHEALTHY",

                "reason":
                    "NO_DISCOVERY_STATUS",

                "complete":
                    None,

                "assets":
                    None,

                "errors":
                    [],
            }

        discovery = (
            cycle.get(
                "discovery",
                {}
            )
            or {}
        )

        complete = discovery.get(
            "complete"
        )

        assets = discovery.get(
            "assets"
        )

        errors = list(
            discovery.get(
                "errors",
                []
            )
            or []
        )

        if complete is True:

            return {
                "status":
                    "HEALTHY",

                "reason":
                    "DISCOVERY_COMPLETE",

                "complete":
                    True,

                "assets":
                    assets,

                "errors":
                    errors,

                "observed_at":
                    discovery.get(
                        "observed_at"
                    ),
            }

        if complete is False:

            return {
                "status":
                    "DEGRADED",

                "reason":
                    "DISCOVERY_INCOMPLETE",

                "complete":
                    False,

                "assets":
                    assets,

                "errors":
                    errors,

                "observed_at":
                    discovery.get(
                        "observed_at"
                    ),
            }

        return {
            "status":
                "UNHEALTHY",

            "reason":
                "DISCOVERY_UNKNOWN",

            "complete":
                None,

            "assets":
                assets,

            "errors":
                errors,

            "observed_at":
                discovery.get(
                    "observed_at"
                ),
        }


    @staticmethod
    def _inventory_component(
        cycle,
    ):

        if cycle is None:

            return {
                "status":
                    "UNHEALTHY",

                "reason":
                    "NO_INVENTORY_STATUS",
            }

        inventory = (
            cycle.get(
                "inventory",
                {}
            )
            or {}
        )

        active = inventory.get(
            "active"
        )

        stale = inventory.get(
            "stale"
        )

        retired = inventory.get(
            "retired"
        )

        transitions = inventory.get(
            "transitions"
        )

        values = (
            active,
            stale,
            retired,
            transitions,
        )

        if any(
            value is None
            for value in values
        ):

            return {
                "status":
                    "DEGRADED",

                "reason":
                    "INVENTORY_NOT_RECONCILED",

                "active":
                    active,

                "stale":
                    stale,

                "retired":
                    retired,

                "transitions":
                    transitions,
            }

        return {
            "status":
                "HEALTHY",

            "reason":
                "INVENTORY_AVAILABLE",

            "active":
                active,

            "stale":
                stale,

            "retired":
                retired,

            "transitions":
                transitions,
        }


    def _ai_component(
        self,
    ):

        try:

            runtime = (
                self.ai_status.status()
            )

        except Exception as exc:

            return {
                "status":
                    "UNHEALTHY",

                "reason":
                    "AI_STATUS_FAILED",

                "error":
                    str(exc),
            }

        runtime = (
            runtime
            if isinstance(
                runtime,
                dict,
            )
            else {}
        )

        raw = str(
            runtime.get(
                "status",
                "UNKNOWN",
            )
            or "UNKNOWN"
        ).upper()

        if raw in (
            "HEALTHY",
            "OK",
        ):

            status = "HEALTHY"
            reason = "AI_RUNTIME_HEALTHY"

        elif raw == "OFFLINE":

            status = "DEGRADED"
            reason = "AI_RUNTIME_OFFLINE"

        elif raw in (
            "DEGRADED",
            "WARNING",
        ):

            status = "DEGRADED"
            reason = "AI_RUNTIME_DEGRADED"

        else:

            status = "UNHEALTHY"
            reason = "AI_RUNTIME_UNHEALTHY"

        return {
            "status":
                status,

            "reason":
                reason,

            "runtime_status":
                raw,

            "runtime":
                runtime.get(
                    "runtime"
                ),

            "target":
                runtime.get(
                    "target"
                ),

            "installed_models":
                runtime.get(
                    "installed_models"
                ),

            "pending_models":
                runtime.get(
                    "pending_models"
                ),
        }


    @staticmethod
    def _overall_status(
        components,
    ):

        statuses = {
            component.get(
                "status",
                "UNHEALTHY",
            )
            for component
            in components.values()
        }

        if "UNHEALTHY" in statuses:
            return "UNHEALTHY"

        if "DEGRADED" in statuses:
            return "DEGRADED"

        return "HEALTHY"


    def status(
        self,
    ):

        cycle = (
            self.status_store.get()
        )

        components = {
            "web_api": {
                "status":
                    "HEALTHY",

                "reason":
                    "REQUEST_SERVED",
            },

            "database":
                self._database_component(),

            "collector":
                self._collector_component(
                    cycle
                ),

            "discovery":
                self._discovery_component(
                    cycle
                ),

            "inventory":
                self._inventory_component(
                    cycle
                ),

            "ai_runtime":
                self._ai_component(),
        }

        overall = (
            self._overall_status(
                components
            )
        )

        return {
            "status":
                overall,

            "scope":
                "ATLAS_CONTROL_PLANE",

            "checked_at":
                self.clock().isoformat(),

            "components":
                components,

            "cycle":
                cycle,

            "freshness_policy": {
                "collector_healthy_seconds":
                    HEALTHY_CYCLE_AGE_SECONDS,

                "collector_degraded_seconds":
                    DEGRADED_CYCLE_AGE_SECONDS,

                "max_running_seconds":
                    MAX_RUNNING_AGE_SECONDS,
            },
        }
