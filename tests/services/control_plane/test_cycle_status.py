from types import SimpleNamespace

import pytest

from atlas.services.collector.worker import (
    CollectorWorker,
)

from atlas.services.control_plane.cycle_status import (
    OperationalCycleStatusStore,
)


def success_result(
    *,
    complete=True,
):

    return {
        "discovery":
            SimpleNamespace(
                complete=complete,
                count=71,
                errors=(
                    []
                    if complete
                    else ["provider failed"]
                ),
                assets=[],
            ),

        "reconciliation": {
            "counts": {
                "ACTIVE": 71,
                "STALE": 0,
                "RETIRED": 10,
            },
            "transitions": [],
        },
    }


def test_cycle_status_initially_absent(
    tmp_path,
):

    store = OperationalCycleStatusStore(
        tmp_path / "atlas.db"
    )

    assert store.get() is None


def test_cycle_status_records_start(
    tmp_path,
):

    store = OperationalCycleStatusStore(
        tmp_path / "atlas.db"
    )

    store.mark_started(
        "2026-09-20T04:00:00+00:00"
    )

    status = store.get()

    assert status["state"] == "RUNNING"

    assert (
        status["started_at"]
        == "2026-09-20T04:00:00+00:00"
    )

    assert status["completed_at"] is None


def test_cycle_status_records_success(
    tmp_path,
):

    store = OperationalCycleStatusStore(
        tmp_path / "atlas.db"
    )

    store.mark_started(
        "2026-09-20T04:00:00+00:00"
    )

    store.mark_success(
        success_result(),
        "2026-09-20T04:00:08+00:00",
    )

    status = store.get()

    assert status["state"] == "SUCCESS"

    assert (
        status["completed_at"]
        == "2026-09-20T04:00:08+00:00"
    )

    assert (
        status["last_success_at"]
        == "2026-09-20T04:00:08+00:00"
    )

    assert status["last_error"] is None

    assert (
        status["discovery"]["complete"]
        is True
    )

    assert (
        status["discovery"]["assets"]
        == 71
    )

    assert (
        status["discovery"]["errors"]
        == []
    )

    assert status["inventory"] == {
        "active": 71,
        "stale": 0,
        "retired": 10,
        "transitions": 0,
    }


def test_failure_preserves_last_good_discovery(
    tmp_path,
):

    store = OperationalCycleStatusStore(
        tmp_path / "atlas.db"
    )

    store.mark_started(
        "2026-09-20T04:00:00+00:00"
    )

    store.mark_success(
        success_result(),
        "2026-09-20T04:00:08+00:00",
    )

    store.mark_started(
        "2026-09-20T04:05:00+00:00"
    )

    store.mark_failed(
        RuntimeError(
            "network unavailable"
        ),
        "2026-09-20T04:05:03+00:00",
    )

    status = store.get()

    assert status["state"] == "FAILED"

    assert (
        status["last_error"]
        == "network unavailable"
    )

    assert (
        status["last_success_at"]
        == "2026-09-20T04:00:08+00:00"
    )

    assert (
        status["discovery"]["complete"]
        is True
    )

    assert (
        status["discovery"]["assets"]
        == 71
    )


class FakeCycle:

    def __init__(
        self,
        result=None,
        error=None,
    ):

        self.result = result
        self.error = error


    def run_once(
        self,
    ):

        if self.error is not None:
            raise self.error

        return self.result


class FakeStatusStore:

    def __init__(
        self,
    ):

        self.calls = []


    def mark_started(
        self,
    ):

        self.calls.append(
            (
                "started",
                None,
            )
        )


    def mark_success(
        self,
        result,
    ):

        self.calls.append(
            (
                "success",
                result,
            )
        )


    def mark_failed(
        self,
        error,
    ):

        self.calls.append(
            (
                "failed",
                str(error),
            )
        )


def test_worker_records_successful_cycle():

    result = success_result()

    status = FakeStatusStore()

    worker = CollectorWorker(
        cycle=FakeCycle(
            result=result
        ),
        status_store=status,
    )

    returned = worker.collect_once()

    assert returned is result

    assert status.calls == [
        (
            "started",
            None,
        ),
        (
            "success",
            result,
        ),
    ]


def test_worker_records_failed_cycle():

    status = FakeStatusStore()

    worker = CollectorWorker(
        cycle=FakeCycle(
            error=RuntimeError(
                "boom"
            )
        ),
        status_store=status,
    )

    with pytest.raises(
        RuntimeError,
        match="boom",
    ):

        worker.collect_once()

    assert status.calls == [
        (
            "started",
            None,
        ),
        (
            "failed",
            "boom",
        ),
    ]


def test_status_read_does_not_create_missing_database(
    tmp_path,
):

    path = (
        tmp_path
        / "missing.db"
    )

    store = OperationalCycleStatusStore(
        path
    )

    assert path.exists() is False

    assert store.get() is None

    assert path.exists() is False
