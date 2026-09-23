from fastapi import FastAPI
from fastapi.testclient import TestClient

from atlas.storage.action_repository import (
    ActionRepository,
)
from atlas.storage.database import Database


TOKEN = "operator-control-center-token"


def build_repository(
    tmp_path,
):

    repository = ActionRepository(
        Database(
            tmp_path
            / "operator-control-center.db"
        )
    )

    repository.save_action_request(
        {
            "id": "pending-action",
            "incident_id": "INC-PENDING",
            "action": "restart container",
            "target": "pending-container",
            "risk": "LOW",
            "rollback": "manual",
            "status": "PENDING_APPROVAL",
            "created_at":
                "2026-09-22T20:00:00+00:00",
            "approved_by": None,
            "approved_at": None,
        }
    )

    repository.save_action_request(
        {
            "id": "rejected-action",
            "incident_id": "INC-REJECTED",
            "action": "stop container",
            "target": "rejected-container",
            "risk": "MEDIUM",
            "rollback": "manual",
            "status": "REJECTED",
            "created_at":
                "2026-09-22T19:00:00+00:00",
            "approved_by": "TEST",
            "approved_at":
                "2026-09-22T19:01:00+00:00",
        }
    )

    repository.save_action_request(
        {
            "id": "verified-action",
            "incident_id": "INC-VERIFIED",
            "action": "restart container",
            "target": "verified-container",
            "risk": "LOW",
            "rollback": "manual",
            "status": "VERIFIED",
            "created_at":
                "2026-09-22T18:00:00+00:00",
            "approved_by": "TEST",
            "approved_at":
                "2026-09-22T18:01:00+00:00",
        }
    )

    repository.finalize_action_verification(
        {
            "approval_id":
                "verified-action",

            "status":
                "VERIFIED",

            "action":
                "restart container",

            "target":
                "verified-container",

            "expected_state":
                "running",

            "observed_state":
                "running",

            "detail":
                "verified",

            "evidence":
                [],

            "verified_at":
                "2026-09-22T18:02:00+00:00",
        },
        "VERIFIED",
    )

    return repository


def build_client(
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

    repository = build_repository(
        tmp_path
    )

    monkeypatch.setattr(
        api,
        "_actions",
        repository,
    )

    app = FastAPI()
    app.include_router(api.router)

    return TestClient(app)


def auth_headers():

    return {
        "Authorization":
            "Bearer " + TOKEN,
    }


def test_control_center_requires_operator_auth(
    tmp_path,
    monkeypatch,
):

    with build_client(
        tmp_path,
        monkeypatch,
    ) as client:

        response = client.get(
            "/api/operator/actions"
        )

    assert response.status_code == 401


def test_control_center_lists_normalized_states(
    tmp_path,
    monkeypatch,
):

    with build_client(
        tmp_path,
        monkeypatch,
    ) as client:

        response = client.get(
            "/api/operator/actions",
            headers=auth_headers(),
        )

    assert response.status_code == 200

    payload = response.json()

    states = {
        item["id"]:
            item["state"]
        for item in payload["actions"]
    }

    assert (
        states["pending-action"]
        == "PENDING_APPROVAL"
    )

    assert (
        states["rejected-action"]
        == "REJECTED"
    )

    assert (
        states["verified-action"]
        == "VERIFIED"
    )

    assert (
        payload["summary"]["VERIFIED"]
        == 1
    )


def test_control_center_filters_by_state(
    tmp_path,
    monkeypatch,
):

    with build_client(
        tmp_path,
        monkeypatch,
    ) as client:

        response = client.get(
            (
                "/api/operator/actions"
                "?state=VERIFIED"
            ),
            headers=auth_headers(),
        )

    assert response.status_code == 200

    payload = response.json()

    assert payload["returned"] == 1

    assert (
        payload["actions"][0]["id"]
        == "verified-action"
    )
