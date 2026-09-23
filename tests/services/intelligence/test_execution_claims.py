"""Durable single-use approvals; all infrastructure handlers are simulated."""

from concurrent.futures import ThreadPoolExecutor
import sqlite3
from threading import Barrier, Lock
from types import SimpleNamespace

import pytest

from atlas.services.intelligence.executor.service import ActionExecutorService
from atlas.storage.action_repository import ActionRepository
from atlas.storage.database import Database


@pytest.fixture
def approved_action(tmp_path):
    database = Database(tmp_path / "operations.db")
    repository = ActionRepository(database)
    approval = {
        "id": "approval-single-use",
        "incident_id": "incident-single-use",
        "action": "restart container",
        "target": "synthetic-service",
        "risk": "LOW",
        "rollback": "docker start synthetic-service",
        "status": "APPROVED",
        "created_at": "2026-09-17T00:00:00+00:00",
        "approved_by": "TEST_OPERATOR",
        "approved_at": "2026-09-17T00:00:00+00:00",
    }
    repository.save_action_request(approval)
    return repository, approval


class AlwaysVerified:

    def verify(
        self,
        action,
        target,
    ):

        return {
            "status":
                "VERIFIED",

            "action":
                action,

            "target":
                target,

            "expected_state":
                "running",

            "observed_state":
                "running",

            "detail":
                "synthetic post-execution verification passed",

            "evidence": [
                "synthetic verification",
            ],

            "verified_at":
                "2026-09-20T06:00:00+00:00",
        }


def executor_with_handler(repository, handler):
    executor = ActionExecutorService(
        repository=repository,
        learning_repository=SimpleNamespace(
            save_learning=lambda record: None
        ),
        verification=AlwaysVerified(),
    )
    executor.execution.docker.restart_container = handler
    return executor


def success(target):
    return {"status": "SUCCESS", "result": target, "evidence": ["simulated"]}


def status(result):
    return result["status"] if isinstance(result, dict) else result.status


def claim_count(repository):
    return repository.database.conn.execute(
        "SELECT count(*) FROM action_execution_claims"
    ).fetchone()[0]


@pytest.mark.parametrize("shared_database", [False, True])
def test_concurrent_requests_execute_once(approved_action, shared_database):
    original, approval = approved_action
    rendezvous = Barrier(2)

    class ConcurrentRepository(ActionRepository):
        def has_action_been_executed(self, approval_id):
            # Both requests must observe no history before either can execute.
            previous = super().has_action_been_executed(approval_id)
            rendezvous.wait(timeout=5)
            return previous

    repositories = [
        ConcurrentRepository(
            original.database if shared_database else Database(original.database.path)
        )
        for _ in range(2)
    ]
    calls = []
    lock = Lock()

    def handler(target):
        with lock:
            calls.append(target)
        return success(target)

    executors = [executor_with_handler(repo, handler) for repo in repositories]
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = [pool.submit(executor.execute, dict(approval)) for executor in executors]
        results = [future.result(timeout=10) for future in pending]

    assert sorted(status(result) for result in results) == ["BLOCKED", "SUCCESS"]
    assert calls == [approval["target"]]
    assert len(original.get_action_history()) == 1
    assert claim_count(original) == 1
    assert original.get_action_request(approval["id"])["status"] == "VERIFIED"


def test_reservation_is_committed_before_handler_runs(approved_action):
    repository, approval = approved_action
    competing = ActionRepository(Database(repository.database.path))
    calls = []

    def handler(target):
        assert claim_count(competing) == 1
        assert competing.claim_action_execution(approval["id"]) is False
        calls.append(target)
        return success(target)

    result = executor_with_handler(repository, handler).execute(approval)
    assert result.status == "SUCCESS"
    assert calls == [approval["target"]]


@pytest.mark.parametrize("failure_stage", ["handler", "history"])
def test_uncertain_execution_cannot_repeat_after_reopening_database(
    approved_action, monkeypatch, failure_stage
):
    repository, approval = approved_action
    calls = []

    def handler(target):
        calls.append(target)
        if failure_stage == "handler":
            raise RuntimeError("simulated interruption after sending command")
        return success(target)

    def failed_history(record):
        raise RuntimeError("simulated interruption before saving result")

    if failure_stage == "history":
        monkeypatch.setattr(repository, "save_action_history", failed_history)

    with pytest.raises(RuntimeError, match="simulated interruption"):
        executor_with_handler(repository, handler).execute(approval)

    assert repository.get_action_history() == []
    # Reopening represents a new worker/process after the interruption.
    reopened = ActionRepository(Database(repository.database.path))
    retry = executor_with_handler(reopened, handler).execute(approval)
    assert retry["status"] == "BLOCKED"
    assert calls == [approval["target"]]
    assert claim_count(reopened) == 1


def test_claim_is_not_released_after_handler_failure(approved_action):
    repository, approval = approved_action
    calls = []

    def failed_handler(target):
        calls.append(target)
        return {"status": "FAILED", "result": "verification failed", "evidence": []}

    executor = executor_with_handler(repository, failed_handler)
    assert executor.execute(approval).status == "FAILED"
    assert executor.execute(approval)["status"] == "BLOCKED"
    assert calls == [approval["target"]]
    assert claim_count(repository) == 1


def test_claim_without_history_survives_restart(approved_action):
    repository, approval = approved_action
    assert repository.claim_action_execution(approval["id"]) is True
    reopened = ActionRepository(Database(repository.database.path))
    assert reopened.get_action_history() == []
    assert reopened.claim_action_execution(approval["id"]) is False


def test_legacy_execution_history_blocks_new_claim(approved_action):
    repository, approval = approved_action
    repository.save_action_history({
        "id": "legacy-execution",
        "approval_id": approval["id"],
        "action": approval["action"],
        "target": approval["target"],
        "status": "FAILED",
        "result": "legacy attempt",
        "executed_at": approval["created_at"],
        "evidence": [],
    })
    assert repository.claim_action_execution(approval["id"]) is False
    assert claim_count(repository) == 0


@pytest.mark.parametrize("current_status", [
    "PENDING_APPROVAL", "REJECTED", "EXECUTED", "VERIFIED",
    "RECOVERY_REQUIRED", "EXECUTION_FAILED", "AUTO_APPROVED",
])
def test_reservation_rechecks_authoritative_approval_state(approved_action, current_status):
    repository, approval = approved_action
    repository.update_action_status(approval["id"], current_status, "TEST_OPERATOR")
    assert repository.claim_action_execution(approval["id"]) is False
    assert claim_count(repository) == 0


def test_nonexistent_approval_cannot_be_reserved(approved_action):
    repository, _ = approved_action
    assert repository.claim_action_execution("unknown-id") is False
    assert claim_count(repository) == 0


def test_reservation_storage_failure_blocks_handler(approved_action, monkeypatch):
    repository, approval = approved_action
    calls = []

    def unavailable(approval_id):
        raise sqlite3.OperationalError("simulated database unavailable")

    def handler(target):
        calls.append(target)
        return success(target)

    monkeypatch.setattr(repository, "claim_action_execution", unavailable)
    result = executor_with_handler(repository, handler).execute(approval)
    assert result["status"] == "BLOCKED"
    assert calls == []
    assert repository.get_action_history() == []


def test_repository_without_atomic_claim_fails_closed(approved_action):
    _, approval = approved_action
    legacy_repository = SimpleNamespace(get_action_request=lambda action_id: dict(approval))
    calls = []

    def handler(target):
        calls.append(target)
        return success(target)

    result = executor_with_handler(legacy_repository, handler).execute(approval)
    assert result["status"] == "BLOCKED"
    assert calls == []


def test_existing_database_gains_claim_table_without_changing_approvals(approved_action):
    repository, approval = approved_action
    repository.database.conn.execute("DROP TABLE action_execution_claims")
    repository.database.conn.commit()
    before = repository.get_action_request(approval["id"])

    reopened = ActionRepository(Database(repository.database.path))
    assert reopened.get_action_request(approval["id"]) == before
    assert reopened.claim_action_execution(approval["id"]) is True
    assert ActionRepository(Database(repository.database.path)).claim_action_execution(
        approval["id"]
    ) is False


def test_in_memory_database_cannot_reserve_a_durable_execution():
    database = Database(":memory:")
    with pytest.raises(ValueError, match="persistent database"):
        database.claim_action_execution("approval")
