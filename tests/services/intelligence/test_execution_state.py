from atlas.storage.action_repository import (
    ActionRepository,
)
from atlas.storage.database import Database


def approval(
    status="APPROVED",
):

    return {
        "id": "approval-recovery-state",
        "incident_id": "incident-recovery-state",
        "action": "restart container",
        "target": "synthetic-service",
        "risk": "LOW",
        "rollback": "docker start synthetic-service",
        "status": status,
        "created_at": "2026-09-17T00:00:00+00:00",
        "approved_by": (
            "TEST_OPERATOR"
            if status == "APPROVED"
            else None
        ),
        "approved_at": (
            "2026-09-17T00:00:00+00:00"
            if status == "APPROVED"
            else None
        ),
    }


def repository(
    tmp_path,
    status="APPROVED",
):

    repo = ActionRepository(
        Database(
            tmp_path
            / "operations.db"
        )
    )

    action = approval(
        status=status
    )

    repo.save_action_request(
        action
    )

    return repo, action


def test_approved_unclaimed_action_is_ready(
    tmp_path,
):

    repo, action = repository(
        tmp_path
    )

    state = (
        repo.get_action_execution_state(
            action["id"]
        )
    )

    assert state == {
        "approval_id": action["id"],
        "action_status": "APPROVED",
        "state": "READY",
        "claimed_at": None,
        "history": None,
        "verification": None,
    }


def test_claim_without_history_is_reserved(
    tmp_path,
):

    repo, action = repository(
        tmp_path
    )

    assert (
        repo.claim_action_execution(
            action["id"]
        )
        is True
    )

    state = (
        repo.get_action_execution_state(
            action["id"]
        )
    )

    assert state["state"] == "RESERVED"
    assert state["claimed_at"]
    assert state["history"] is None


def test_history_makes_result_recorded(
    tmp_path,
):

    repo, action = repository(
        tmp_path
    )

    assert (
        repo.claim_action_execution(
            action["id"]
        )
        is True
    )

    repo.save_action_history(
        {
            "id":
                "execution-recovery-state",

            "approval_id":
                action["id"],

            "action":
                action["action"],

            "target":
                action["target"],

            "status":
                "FAILED",

            "result":
                "verification failed",

            "executed_at":
                "2026-09-17T00:01:00+00:00",

            "evidence":
                [],
        }
    )

    state = (
        repo.get_action_execution_state(
            action["id"]
        )
    )

    assert state["state"] == "RECORDED"

    assert state["history"] == {
        "id":
            "execution-recovery-state",

        "status":
            "FAILED",

        "result":
            "verification failed",

        "executed_at":
            "2026-09-17T00:01:00+00:00",
    }


def test_pending_action_is_not_ready(
    tmp_path,
):

    repo, action = repository(
        tmp_path,
        status="PENDING_APPROVAL",
    )

    state = (
        repo.get_action_execution_state(
            action["id"]
        )
    )

    assert state["state"] == "NOT_READY"
    assert state["claimed_at"] is None
    assert state["history"] is None


def test_unknown_action_has_no_execution_state(
    tmp_path,
):

    repo = ActionRepository(
        Database(
            tmp_path
            / "operations.db"
        )
    )

    assert (
        repo.get_action_execution_state(
            "unknown-action"
        )
        is None
    )


def test_reserved_state_survives_database_reopen(
    tmp_path,
):

    path = (
        tmp_path
        / "operations.db"
    )

    first = ActionRepository(
        Database(path)
    )

    action = approval()

    first.save_action_request(
        action
    )

    assert (
        first.claim_action_execution(
            action["id"]
        )
        is True
    )

    first.database.conn.close()

    reopened = ActionRepository(
        Database(path)
    )

    state = (
        reopened.get_action_execution_state(
            action["id"]
        )
    )

    assert state["approval_id"] == action["id"]
    assert state["action_status"] == "APPROVED"
    assert state["state"] == "RESERVED"
    assert state["claimed_at"]
    assert state["history"] is None

    # Recovery inspection must never make the
    # approval executable again.
    assert (
        reopened.claim_action_execution(
            action["id"]
        )
        is False
    )
