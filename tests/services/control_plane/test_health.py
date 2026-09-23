from datetime import (
    UTC,
    datetime,
)

from atlas.services.control_plane.health import (
    ControlPlaneHealthService,
)

from atlas.services.control_plane.cycle_status import (
    OperationalCycleStatusStore,
)


NOW = datetime(
    2026,
    9,
    20,
    4,
    20,
    0,
    tzinfo=UTC,
)


class FakeAIStatus:

    def __init__(
        self,
        status="HEALTHY",
    ):

        self.value = status


    def status(
        self,
    ):

        return {
            "status":
                self.value,

            "runtime":
                "ollama",

            "target": {
                "host":
                    "atlas-ai",
                "port":
                    11434,
            },

            "installed_models":
                5,

            "pending_models":
                0,
        }


class FakeStatusStore:

    def __init__(
        self,
        value,
    ):

        self.value = value


    def get(
        self,
    ):

        return self.value


def cycle_status(
    *,
    state="SUCCESS",
    success_at="2026-09-20T04:15:00+00:00",
    started_at="2026-09-20T04:14:52+00:00",
    complete=True,
    active=71,
    stale=0,
    retired=10,
    transitions=0,
    error=None,
):

    return {
        "state":
            state,

        "started_at":
            started_at,

        "completed_at":
            success_at,

        "last_success_at":
            success_at,

        "last_error":
            error,

        "discovery": {
            "observed_at":
                success_at,

            "complete":
                complete,

            "assets":
                71,

            "errors":
                (
                    []
                    if complete
                    else ["provider failed"]
                ),
        },

        "inventory": {
            "active":
                active,

            "stale":
                stale,

            "retired":
                retired,

            "transitions":
                transitions,
        },

        "updated_at":
            success_at,
    }


def make_service(
    tmp_path,
    cycle,
    ai="HEALTHY",
):

    database = (
        tmp_path
        / "atlas.db"
    )

    OperationalCycleStatusStore(
        database
    ).mark_started(
        "2026-09-20T04:00:00+00:00"
    )

    return ControlPlaneHealthService(
        status_store=FakeStatusStore(
            cycle
        ),
        ai_status=FakeAIStatus(
            ai
        ),
        database_path=database,
        clock=lambda: NOW,
    )


def test_fresh_control_plane_is_healthy(
    tmp_path,
):

    result = make_service(
        tmp_path,
        cycle_status(),
    ).status()

    assert result["status"] == "HEALTHY"

    assert (
        result["scope"]
        == "ATLAS_CONTROL_PLANE"
    )

    assert (
        result["components"]["database"]["status"]
        == "HEALTHY"
    )

    assert (
        result["components"]["collector"]["status"]
        == "HEALTHY"
    )

    assert (
        result["components"]["discovery"]["status"]
        == "HEALTHY"
    )

    assert (
        result["components"]["inventory"]["active"]
        == 71
    )

    assert (
        result["components"]["ai_runtime"]["status"]
        == "HEALTHY"
    )


def test_collector_becomes_degraded_after_healthy_window(
    tmp_path,
):

    result = make_service(
        tmp_path,
        cycle_status(
            success_at=
                "2026-09-20T04:09:00+00:00"
        ),
    ).status()

    collector = (
        result["components"]["collector"]
    )

    assert collector["status"] == "DEGRADED"
    assert collector["reason"] == "CYCLE_STALE"
    assert collector["age_seconds"] == 660

    assert result["status"] == "DEGRADED"


def test_collector_becomes_unhealthy_after_expiry(
    tmp_path,
):

    result = make_service(
        tmp_path,
        cycle_status(
            success_at=
                "2026-09-20T04:04:59+00:00"
        ),
    ).status()

    collector = (
        result["components"]["collector"]
    )

    assert collector["status"] == "UNHEALTHY"
    assert collector["reason"] == "CYCLE_EXPIRED"

    assert result["status"] == "UNHEALTHY"


def test_latest_failed_cycle_is_unhealthy(
    tmp_path,
):

    result = make_service(
        tmp_path,
        cycle_status(
            state="FAILED",
            error="network unavailable",
        ),
    ).status()

    collector = (
        result["components"]["collector"]
    )

    assert collector["status"] == "UNHEALTHY"
    assert collector["reason"] == "LAST_CYCLE_FAILED"
    assert collector["error"] == "network unavailable"

    assert result["status"] == "UNHEALTHY"


def test_recent_running_cycle_is_not_false_alarm(
    tmp_path,
):

    result = make_service(
        tmp_path,
        cycle_status(
            state="RUNNING",
            started_at=
                "2026-09-20T04:19:30+00:00",
        ),
    ).status()

    collector = (
        result["components"]["collector"]
    )

    assert collector["status"] == "HEALTHY"
    assert collector["reason"] == "CYCLE_RUNNING"


def test_stuck_running_cycle_is_unhealthy(
    tmp_path,
):

    result = make_service(
        tmp_path,
        cycle_status(
            state="RUNNING",
            started_at=
                "2026-09-20T04:17:00+00:00",
        ),
    ).status()

    collector = (
        result["components"]["collector"]
    )

    assert collector["status"] == "UNHEALTHY"

    assert (
        collector["reason"]
        == "CYCLE_RUNNING_TOO_LONG"
    )


def test_incomplete_discovery_degrades_control_plane(
    tmp_path,
):

    value = cycle_status(
        complete=False,
        active=None,
        stale=None,
        retired=None,
        transitions=None,
    )

    result = make_service(
        tmp_path,
        value,
    ).status()

    assert (
        result["components"]["discovery"]["status"]
        == "DEGRADED"
    )

    assert (
        result["components"]["inventory"]["status"]
        == "DEGRADED"
    )

    assert result["status"] == "DEGRADED"


def test_ai_failure_affects_overall_health(
    tmp_path,
):

    result = make_service(
        tmp_path,
        cycle_status(),
        ai="UNHEALTHY",
    ).status()

    assert (
        result["components"]["ai_runtime"]["status"]
        == "UNHEALTHY"
    )

    assert result["status"] == "UNHEALTHY"


def test_missing_database_is_unhealthy(
    tmp_path,
):

    missing = (
        tmp_path
        / "missing.db"
    )

    service = ControlPlaneHealthService(
        status_store=FakeStatusStore(
            cycle_status()
        ),
        ai_status=FakeAIStatus(),
        database_path=missing,
        clock=lambda: NOW,
    )

    result = service.status()

    assert (
        result["components"]["database"]["status"]
        == "UNHEALTHY"
    )

    assert (
        result["components"]["database"]["reason"]
        == "DATABASE_NOT_FOUND"
    )

    assert result["status"] == "UNHEALTHY"
