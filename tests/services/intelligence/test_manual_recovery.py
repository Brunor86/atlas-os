from atlas.services.intelligence.recovery.service import (
    ActionRecoveryService,
)
from atlas.storage.action_repository import (
    ActionRepository,
)
from atlas.storage.database import Database


class FakeVerification:

    def __init__(
        self,
        status,
        observed_state,
    ):

        self.status = status
        self.observed_state = observed_state
        self.calls = []


    def verify(
        self,
        action,
        target,
    ):

        self.calls.append(
            (
                action,
                target,
            )
        )

        return {
            "status":
                self.status,

            "action":
                action,

            "target":
                target,

            "expected_state":
                "running",

            "observed_state":
                self.observed_state,

            "detail":
                (
                    "manual verification passed"
                    if self.status == "VERIFIED"
                    else "manual verification failed"
                ),

            "evidence": [
                "synthetic manual verification",
            ],

            "verified_at":
                "2026-09-22T18:00:00+00:00",
        }


def seed_recovery_required(
    repository,
    *,
    action_id="manual-recovery-action",
):

    action = {
        "id":
            action_id,

        "incident_id":
            "INC-MANUAL-RECOVERY",

        "action":
            "restart container",

        "target":
            "synthetic-container",

        "risk":
            "LOW",

        "rollback":
            "manual rollback",

        "status":
            "APPROVED",

        "created_at":
            "2026-09-22T17:00:00+00:00",

        "approved_by":
            "TEST_OPERATOR",

        "approved_at":
            "2026-09-22T17:00:00+00:00",
    }

    repository.save_action_request(
        action
    )

    assert (
        repository.claim_action_execution(
            action_id
        )
        is True
    )

    repository.save_action_history(
        {
            "id":
                "execution-" + action_id,

            "approval_id":
                action_id,

            "action":
                action["action"],

            "target":
                action["target"],

            "status":
                "SUCCESS",

            "result":
                "command returned success",

            "executed_at":
                "2026-09-22T17:01:00+00:00",

            "evidence": [
                "synthetic execution",
            ],
        }
    )

    repository.finalize_action_verification(
        {
            "approval_id":
                action_id,

            "status":
                "RECOVERY_REQUIRED",

            "action":
                action["action"],

            "target":
                action["target"],

            "expected_state":
                "running",

            "observed_state":
                "stopped",

            "detail":
                "initial verification failed",

            "evidence": [
                "initial verification evidence",
            ],

            "verified_at":
                "2026-09-22T17:02:00+00:00",
        },
        "RECOVERY_REQUIRED",
    )

    return action


def test_manual_reverification_can_resolve_recovery_required(
    tmp_path,
):

    repository = ActionRepository(
        Database(
            tmp_path
            / "manual-recovery.db"
        )
    )

    action = seed_recovery_required(
        repository
    )

    verifier = FakeVerification(
        "VERIFIED",
        "running",
    )

    recovery = ActionRecoveryService(
        repository=repository,
        verification=verifier,
    )


    result = recovery.reverify(
        action["id"],
        requested_by="TEST_OPERATOR",
    )


    assert result["status"] == "VERIFIED"

    assert verifier.calls == [
        (
            "restart container",
            "synthetic-container",
        )
    ]

    persisted = (
        repository.get_action_request(
            action["id"]
        )
    )

    assert persisted["status"] == "VERIFIED"

    state = (
        repository
        .get_action_execution_state(
            action["id"]
        )
    )

    assert state["state"] == "VERIFIED"

    assert (
        state["history"]["status"]
        == "SUCCESS"
    )

    # The durable execution claim still blocks replay.
    assert (
        repository.claim_action_execution(
            action["id"]
        )
        is False
    )


    verification_history = (
        repository
        .get_action_verification_history(
            action["id"]
        )
    )

    assert len(
        verification_history
    ) == 2

    assert (
        verification_history[0]["status"]
        == "RECOVERY_REQUIRED"
    )

    assert (
        verification_history[0]["source"]
        == "POST_EXECUTION"
    )

    assert (
        verification_history[1]["status"]
        == "VERIFIED"
    )

    assert (
        verification_history[1]["source"]
        == "MANUAL_REVERIFY"
    )

    assert (
        verification_history[1][
            "requested_by"
        ]
        == "TEST_OPERATOR"
    )


def test_failed_manual_reverification_remains_recovery_required(
    tmp_path,
):

    repository = ActionRepository(
        Database(
            tmp_path
            / "manual-recovery-failed.db"
        )
    )

    action = seed_recovery_required(
        repository
    )

    recovery = ActionRecoveryService(
        repository=repository,
        verification=FakeVerification(
            "RECOVERY_REQUIRED",
            "stopped",
        ),
    )


    result = recovery.reverify(
        action["id"],
        requested_by="TEST_OPERATOR",
    )


    assert (
        result["status"]
        == "RECOVERY_REQUIRED"
    )

    assert (
        repository
        .get_action_request(
            action["id"]
        )["status"]
        == "RECOVERY_REQUIRED"
    )

    assert (
        repository
        .get_action_execution_state(
            action["id"]
        )["state"]
        == "RECOVERY_REQUIRED"
    )

    assert len(
        repository
        .get_action_verification_history(
            action["id"]
        )
    ) == 2


def test_manual_reverification_refuses_non_recovery_action(
    tmp_path,
):

    repository = ActionRepository(
        Database(
            tmp_path
            / "manual-recovery-blocked.db"
        )
    )

    action = {
        "id":
            "not-recovery",

        "incident_id":
            "INC-NOT-RECOVERY",

        "action":
            "restart container",

        "target":
            "synthetic-container",

        "risk":
            "LOW",

        "rollback":
            "manual rollback",

        "status":
            "APPROVED",

        "created_at":
            "2026-09-22T17:00:00+00:00",

        "approved_by":
            "TEST_OPERATOR",

        "approved_at":
            "2026-09-22T17:00:00+00:00",
    }

    repository.save_action_request(
        action
    )

    verifier = FakeVerification(
        "VERIFIED",
        "running",
    )

    recovery = ActionRecoveryService(
        repository=repository,
        verification=verifier,
    )


    try:

        recovery.reverify(
            action["id"],
            requested_by="TEST_OPERATOR",
        )

    except ValueError as exc:

        assert (
            "RECOVERY_REQUIRED"
            in str(exc)
        )

    else:

        raise AssertionError(
            "non-recovery action was accepted"
        )


    assert verifier.calls == []



def test_stale_reverification_cannot_regress_verified_state(
    tmp_path,
):

    repository = ActionRepository(
        Database(
            tmp_path
            / "manual-recovery-race.db"
        )
    )

    action = seed_recovery_required(
        repository,
        action_id="manual-recovery-race",
    )


    verified = {
        "approval_id":
            action["id"],

        "status":
            "VERIFIED",

        "action":
            action["action"],

        "target":
            action["target"],

        "expected_state":
            "running",

        "observed_state":
            "running",

        "detail":
            "first recovery verifier passed",

        "evidence": [
            "first verifier",
        ],

        "verified_at":
            "2026-09-22T18:20:00+00:00",

        "source":
            "MANUAL_REVERIFY",

        "requested_by":
            "OPERATOR_A",
    }


    accepted = (
        repository
        .finalize_action_verification(
            verified,
            "VERIFIED",
            expected_current_status=(
                "RECOVERY_REQUIRED"
            ),
        )
    )

    assert accepted is not False


    stale_failure = {
        "approval_id":
            action["id"],

        "status":
            "RECOVERY_REQUIRED",

        "action":
            action["action"],

        "target":
            action["target"],

        "expected_state":
            "running",

        "observed_state":
            "stopped",

        "detail":
            "stale concurrent verifier failed",

        "evidence": [
            "stale second verifier",
        ],

        "verified_at":
            "2026-09-22T18:21:00+00:00",

        "source":
            "MANUAL_REVERIFY",

        "requested_by":
            "OPERATOR_B",
    }


    rejected = (
        repository
        .finalize_action_verification(
            stale_failure,
            "RECOVERY_REQUIRED",
            expected_current_status=(
                "RECOVERY_REQUIRED"
            ),
        )
    )


    assert rejected is False


    persisted = (
        repository.get_action_request(
            action["id"]
        )
    )

    assert persisted["status"] == "VERIFIED"


    verification = (
        repository
        .get_action_verification(
            action["id"]
        )
    )

    assert (
        verification["status"]
        == "VERIFIED"
    )

    assert (
        verification["observed_state"]
        == "running"
    )


    history = (
        repository
        .get_action_verification_history(
            action["id"]
        )
    )

    # Initial failure + successful recovery.
    # The stale result must never enter the durable audit trail.
    assert len(history) == 2

    assert [
        item["status"]
        for item in history
    ] == [
        "RECOVERY_REQUIRED",
        "VERIFIED",
    ]
