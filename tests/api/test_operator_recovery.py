from fastapi import FastAPI
from fastapi.testclient import TestClient

from atlas.services.intelligence.recovery.service import (
    ActionRecoveryService,
)
from atlas.storage.action_repository import (
    ActionRepository,
)
from atlas.storage.database import Database


TOKEN = "test-manual-recovery-token"


class FakeVerification:

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
                "manual recovery verified",

            "evidence": [
                "API recovery test",
            ],

            "verified_at":
                "2026-09-22T18:10:00+00:00",
        }


def test_operator_can_manually_reverify_recovery_required(
    tmp_path,
    monkeypatch,
):

    from atlas.api import (
        operator_actions as api,
    )


    monkeypatch.setenv(
        "ATLAS_OPERATOR_TOKEN",
        TOKEN,
    )


    repository = ActionRepository(
        Database(
            tmp_path
            / "operator-recovery.db"
        )
    )


    action = {
        "id":
            "api-manual-recovery",

        "incident_id":
            "INC-API-RECOVERY",

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
            action["id"]
        )
        is True
    )

    repository.save_action_history(
        {
            "id":
                "execution-api-manual-recovery",

            "approval_id":
                action["id"],

            "action":
                action["action"],

            "target":
                action["target"],

            "status":
                "SUCCESS",

            "result":
                "command success",

            "executed_at":
                "2026-09-22T17:01:00+00:00",

            "evidence":
                [],
        }
    )

    repository.finalize_action_verification(
        {
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
                "initial verification failed",

            "evidence":
                [],

            "verified_at":
                "2026-09-22T17:02:00+00:00",
        },
        "RECOVERY_REQUIRED",
    )


    monkeypatch.setattr(
        api,
        "_actions",
        repository,
    )

    monkeypatch.setattr(
        api,
        "_recovery",
        ActionRecoveryService(
            repository=repository,
            verification=FakeVerification(),
        ),
    )


    app = FastAPI()

    app.include_router(
        api.router
    )


    with TestClient(app) as client:

        response = client.post(
            "/api/operator/actions/"
            + action["id"]
            + "/reverify",
            headers={
                "Authorization":
                    "Bearer " + TOKEN,
            },
        )


    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "VERIFIED"

    assert (
        payload["action_request"]["status"]
        == "VERIFIED"
    )

    assert (
        payload["execution_state"]["state"]
        == "VERIFIED"
    )

    assert len(
        payload["verification_history"]
    ) == 2

    assert (
        payload[
            "verification_history"
        ][1]["source"]
        == "MANUAL_REVERIFY"
    )

    assert (
        payload[
            "verification_history"
        ][1]["requested_by"]
        == "ATLAS_WEB_OPERATOR"
    )


    with TestClient(app) as client:

        inspection = client.get(
            "/api/operator/actions/"
            + action["id"],
            headers={
                "Authorization":
                    "Bearer " + TOKEN,
            },
        )


    assert inspection.status_code == 200

    inspected = inspection.json()

    assert (
        inspected["execution_state"]["state"]
        == "VERIFIED"
    )

    assert len(
        inspected["verification_history"]
    ) == 2

    assert [
        item["status"]
        for item in inspected[
            "verification_history"
        ]
    ] == [
        "RECOVERY_REQUIRED",
        "VERIFIED",
    ]
