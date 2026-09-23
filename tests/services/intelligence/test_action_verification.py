from types import (
    SimpleNamespace,
)

from atlas.services.intelligence.executor.service import (
    ActionExecutorService,
)

from atlas.services.intelligence.verification.service import (
    ActionVerificationService,
)

from atlas.storage.action_repository import (
    ActionRepository,
)

from atlas.storage.database import (
    Database,
)


def approved_action(
    repository,
    *,
    action="restart container",
    target="synthetic-container",
    action_id="verification-action",
):

    record = {
        "id":
            action_id,

        "incident_id":
            "INC-VERIFICATION",

        "action":
            action,

        "target":
            target,

        "risk":
            "LOW",

        "rollback":
            "manual rollback",

        "status":
            "APPROVED",

        "created_at":
            "2026-09-20T06:00:00+00:00",

        "approved_by":
            "TEST_OPERATOR",

        "approved_at":
            "2026-09-20T06:00:00+00:00",
    }

    repository.save_action_request(
        record
    )

    return record


class FakeVerification:

    def __init__(
        self,
        status,
        observed,
    ):

        self.status = status
        self.observed = observed
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
                self.observed,

            "detail":
                (
                    "verification passed"
                    if self.status == "VERIFIED"
                    else "verification failed"
                ),

            "evidence": [
                "synthetic independent verification",
            ],

            "verified_at":
                "2026-09-20T06:01:00+00:00",
        }


def build_executor(
    repository,
    verification,
    handler,
):

    executor = ActionExecutorService(
        repository=repository,
        learning_repository=repository,
        verification=verification,
    )

    executor.execution.docker.restart_container = (
        handler
    )

    return executor


def test_successful_command_becomes_verified(
    tmp_path,
):

    repository = ActionRepository(
        Database(
            tmp_path
            / "verified.db"
        )
    )

    approval = approved_action(
        repository
    )

    verifier = FakeVerification(
        "VERIFIED",
        "running",
    )

    executor = build_executor(
        repository,
        verifier,
        lambda target: {
            "status":
                "SUCCESS",

            "result":
                target,

            "evidence": [
                "command succeeded",
            ],
        },
    )


    result = executor.execute(
        approval
    )


    assert result.status == "SUCCESS"

    assert (
        result.verification[
            "status"
        ]
        == "VERIFIED"
    )

    assert verifier.calls == [
        (
            "restart container",
            "synthetic-container",
        )
    ]


    persisted = (
        repository
        .get_action_request(
            approval["id"]
        )
    )

    assert (
        persisted["status"]
        == "VERIFIED"
    )


    verification = (
        repository
        .get_action_verification(
            approval["id"]
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


    state = (
        repository
        .get_action_execution_state(
            approval["id"]
        )
    )

    assert state["state"] == "VERIFIED"

    assert (
        state[
            "history"
        ][
            "status"
        ]
        == "SUCCESS"
    )

    assert (
        state[
            "verification"
        ][
            "status"
        ]
        == "VERIFIED"
    )


    learning = (
        repository
        .database
        .conn.execute(
            """
            SELECT
                result,
                confidence
            FROM learning_records
            ORDER BY id DESC
            LIMIT 1
            """
        )
        .fetchone()
    )

    assert learning[0] == "VERIFIED"
    assert learning[1] == 1.0


def test_successful_command_with_failed_verification_requires_recovery(
    tmp_path,
):

    repository = ActionRepository(
        Database(
            tmp_path
            / "recovery-required.db"
        )
    )

    approval = approved_action(
        repository
    )

    verifier = FakeVerification(
        "RECOVERY_REQUIRED",
        "stopped",
    )

    executor = build_executor(
        repository,
        verifier,
        lambda target: {
            "status":
                "SUCCESS",

            "result":
                target,

            "evidence": [
                "command returned success",
            ],
        },
    )


    result = executor.execute(
        approval
    )


    assert result.status == "SUCCESS"

    assert (
        result.verification[
            "status"
        ]
        == "RECOVERY_REQUIRED"
    )


    persisted = (
        repository
        .get_action_request(
            approval["id"]
        )
    )

    assert (
        persisted["status"]
        == "RECOVERY_REQUIRED"
    )


    state = (
        repository
        .get_action_execution_state(
            approval["id"]
        )
    )

    assert (
        state["state"]
        == "RECOVERY_REQUIRED"
    )

    assert (
        state[
            "history"
        ][
            "status"
        ]
        == "SUCCESS"
    )


    #
    # Command already ran. Recovery state must never allow
    # the same approval to execute again.
    #
    replay = executor.execute(
        approval
    )

    assert replay["status"] == "BLOCKED"


def test_command_failure_is_execution_failed_without_verification(
    tmp_path,
):

    repository = ActionRepository(
        Database(
            tmp_path
            / "execution-failed.db"
        )
    )

    approval = approved_action(
        repository
    )

    verifier = FakeVerification(
        "VERIFIED",
        "running",
    )

    executor = build_executor(
        repository,
        verifier,
        lambda target: {
            "status":
                "FAILED",

            "result":
                "command failed",

            "evidence": [
                "synthetic failure",
            ],
        },
    )


    result = executor.execute(
        approval
    )


    assert result.status == "FAILED"
    assert verifier.calls == []


    persisted = (
        repository
        .get_action_request(
            approval["id"]
        )
    )

    assert (
        persisted["status"]
        == "EXECUTION_FAILED"
    )


    assert (
        repository
        .get_action_verification(
            approval["id"]
        )
        is None
    )


    state = (
        repository
        .get_action_execution_state(
            approval["id"]
        )
    )

    assert (
        state["state"]
        == "EXECUTION_FAILED"
    )

    assert (
        state[
            "history"
        ][
            "status"
        ]
        == "FAILED"
    )


def test_verifier_exception_fails_closed_to_recovery_required(
    tmp_path,
):

    repository = ActionRepository(
        Database(
            tmp_path
            / "verification-exception.db"
        )
    )

    approval = approved_action(
        repository
    )


    class BrokenVerification:

        def verify(
            self,
            action,
            target,
        ):

            raise RuntimeError(
                "synthetic verifier unavailable"
            )


    executor = build_executor(
        repository,
        BrokenVerification(),
        lambda target: {
            "status":
                "SUCCESS",

            "result":
                target,

            "evidence": [
                "command succeeded",
            ],
        },
    )


    result = executor.execute(
        approval
    )


    assert (
        result.verification[
            "status"
        ]
        == "RECOVERY_REQUIRED"
    )

    assert (
        repository
        .get_action_request(
            approval["id"]
        )[
            "status"
        ]
        == "RECOVERY_REQUIRED"
    )


def test_docker_verifier_observes_running_state():

    def runner(
        args,
        **kwargs,
    ):

        assert args[:3] == [
            "docker",
            "inspect",
            "-f",
        ]

        return SimpleNamespace(
            returncode=0,
            stdout="true\n",
            stderr="",
        )


    verifier = ActionVerificationService(
        runner=runner
    )

    result = verifier.verify(
        "restart container",
        "nginx-proxy-manager",
    )

    assert result["status"] == "VERIFIED"
    assert result["expected_state"] == "running"
    assert result["observed_state"] == "running"


def test_docker_verifier_detects_wrong_state():

    def runner(
        args,
        **kwargs,
    ):

        return SimpleNamespace(
            returncode=0,
            stdout="false\n",
            stderr="",
        )


    verifier = ActionVerificationService(
        runner=runner
    )

    result = verifier.verify(
        "start container",
        "nginx-proxy-manager",
    )

    assert (
        result["status"]
        == "RECOVERY_REQUIRED"
    )

    assert (
        result["observed_state"]
        == "stopped"
    )


def test_systemd_verifier_observes_active_state():

    def runner(
        args,
        **kwargs,
    ):

        assert args[0] == "systemctl"

        return SimpleNamespace(
            returncode=0,
            stdout="active\n",
            stderr="",
        )


    verifier = ActionVerificationService(
        runner=runner
    )

    result = verifier.verify(
        "restart service",
        "atlas-collector.service",
    )

    assert result["status"] == "VERIFIED"
    assert result["observed_state"] == "active"


def test_proxmox_verifier_observes_qemu_state():

    class FakeProxmox:

        def resolve_guest(
            self,
            vmid,
            expected_type=None,
        ):

            assert vmid == 300
            assert expected_type == "qemu"

            return SimpleNamespace(
                status="running"
            )


    verifier = ActionVerificationService(
        proxmox=FakeProxmox()
    )

    result = verifier.verify(
        "restart vm",
        "300",
    )

    assert result["status"] == "VERIFIED"
    assert result["observed_state"] == "running"


def test_unknown_verification_route_fails_closed():

    verifier = ActionVerificationService()

    result = verifier.verify(
        "future action",
        "target",
    )

    assert (
        result["status"]
        == "RECOVERY_REQUIRED"
    )

    assert (
        result["observed_state"]
        == "unsupported"
    )


def test_verification_table_and_final_state_are_persistent(
    tmp_path,
):

    path = (
        tmp_path
        / "verification-persistence.db"
    )

    first = ActionRepository(
        Database(
            path
        )
    )

    approval = approved_action(
        first,
        action_id=
            "persistent-verification",
    )

    first.finalize_action_verification(
        {
            "approval_id":
                approval["id"],

            "status":
                "VERIFIED",

            "action":
                approval["action"],

            "target":
                approval["target"],

            "expected_state":
                "running",

            "observed_state":
                "running",

            "detail":
                "persistent verification",

            "evidence": [
                "persistent evidence",
            ],

            "verified_at":
                "2026-09-20T06:05:00+00:00",
        },
        "VERIFIED",
    )


    reopened = ActionRepository(
        Database(
            path
        )
    )


    assert (
        reopened
        .get_action_request(
            approval["id"]
        )[
            "status"
        ]
        == "VERIFIED"
    )


    verification = (
        reopened
        .get_action_verification(
            approval["id"]
        )
    )


    assert verification == {
        "approval_id":
            approval["id"],

        "status":
            "VERIFIED",

        "action":
            approval["action"],

        "target":
            approval["target"],

        "expected_state":
            "running",

        "observed_state":
            "running",

        "detail":
            "persistent verification",

        "evidence": [
            "persistent evidence",
        ],

        "verified_at":
            "2026-09-20T06:05:00+00:00",
    }
