from types import SimpleNamespace
import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from atlas.core.asset import (
    Asset,
    AssetType,
    Capability,
    Criticality,
    ServiceImportance,
)


OPERATOR_TOKEN = "test-operator-token"

AUTH_HEADERS = {
    "Authorization":
        f"Bearer {OPERATOR_TOKEN}",
}


class _AllowingOperatorAssetRepository:

    def __init__(
        self,
    ):

        self.target = None


    def find_by_identity(
        self,
        identity,
    ):

        assert identity.vendor == "Docker"

        self.target = identity.serial

        return (
            "test-asset:"
            + str(identity.serial)
        )


    def get_asset(
        self,
        asset_id,
    ):

        return Asset(
            id=asset_id,
            name=str(
                self.target
                or "synthetic-container"
            ),
            type=AssetType.APPLICATION,
            criticality=Criticality.MEDIUM,
            service_importance=(
                ServiceImportance.NORMAL
            ),
            capabilities={
                Capability.START,
                Capability.STOP,
                Capability.RESTART,
            },
        )


@pytest.fixture(autouse=True)
def configured_operator_token(
    monkeypatch,
):

    monkeypatch.setenv(
        "ATLAS_OPERATOR_TOKEN",
        OPERATOR_TOKEN,
    )

    from atlas.api import (
        operator_actions as api,
    )

    monkeypatch.setattr(
        api,
        "_asset_repository",
        _AllowingOperatorAssetRepository(),
    )


def test_api_preserves_blocked_status_when_reservation_fails(monkeypatch):
    from atlas.api import operator_actions as api
    from atlas.services.intelligence.approval.service import ActionApprovalService
    from atlas.services.intelligence.executor.service import ActionExecutorService
    from atlas.storage.action_repository import ActionRepository
    from atlas.storage.database import Database

    repository = ActionRepository(Database())
    approval = {
        "id": "api-reservation-failure",
        "incident_id": "synthetic-incident",
        "action": "restart container",
        "target": "synthetic-container",
        "risk": "LOW",
        "rollback": "docker start synthetic-container",
        "status": "PENDING_APPROVAL",
        "created_at": "2026-09-17T00:00:00+00:00",
        "approved_by": None,
        "approved_at": None,
    }
    repository.save_action_request(approval)
    executor = ActionExecutorService(repository=repository)
    calls = []

    def unavailable(approval_id):
        raise sqlite3.OperationalError("simulated reservation failure")

    def unexpected_handler(target):
        calls.append(target)
        raise AssertionError("unreserved execution must not reach infrastructure")

    monkeypatch.setattr(repository, "claim_action_execution", unavailable)
    monkeypatch.setattr(executor.execution.docker, "restart_container", unexpected_handler)
    monkeypatch.setattr(api, "_actions", repository)
    monkeypatch.setattr(api, "_approval", ActionApprovalService(
        action_repository=repository,
        lifecycle_repository=SimpleNamespace(save=lambda event: event),
    ))
    monkeypatch.setattr(api, "_executor", executor)

    app = FastAPI()
    app.include_router(api.router)
    with TestClient(app) as client:
        response = client.post(
            "/api/operator/actions/"
            "api-reservation-failure/approve",
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == payload["execution"]["status"] == "BLOCKED"
    assert payload["execution"]["approval_id"] == approval["id"]
    assert calls == []
    assert repository.get_action_history() == []


def test_api_get_action_exposes_execution_state(
    tmp_path,
    monkeypatch,
):

    from atlas.api import operator_actions as api
    from atlas.storage.action_repository import (
        ActionRepository,
    )
    from atlas.storage.database import Database

    repository = ActionRepository(
        Database(
            tmp_path
            / "operator-state.db"
        )
    )

    action = {
        "id": "api-execution-state",
        "incident_id": "api-execution-state-incident",
        "action": "restart container",
        "target": "synthetic-container",
        "risk": "LOW",
        "rollback": "docker start synthetic-container",
        "status": "APPROVED",
        "created_at": "2026-09-17T00:00:00+00:00",
        "approved_by": "TEST_OPERATOR",
        "approved_at": "2026-09-17T00:00:00+00:00",
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

    monkeypatch.setattr(
        api,
        "_actions",
        repository,
    )

    app = FastAPI()
    app.include_router(api.router)

    with TestClient(app) as client:
        response = client.get(
            "/api/operator/actions/"
            + action["id"],
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 200

    payload = response.json()

    assert (
        payload["action_request"]["id"]
        == action["id"]
    )

    assert (
        payload["execution_state"]["state"]
        == "RESERVED"
    )

    assert (
        payload["execution_state"]["claimed_at"]
    )

    assert (
        payload["execution_state"]["history"]
        is None
    )


def test_api_approve_exposes_recorded_execution_state(
    tmp_path,
    monkeypatch,
):

    from atlas.api import operator_actions as api

    from atlas.services.intelligence.approval.service import (
        ActionApprovalService,
    )

    from atlas.services.intelligence.executor.service import (
        ActionExecutorService,
    )

    from atlas.storage.action_repository import (
        ActionRepository,
    )

    from atlas.storage.database import Database


    repository = ActionRepository(
        Database(
            tmp_path
            / "operator-approve-state.db"
        )
    )

    approval = {
        "id":
            "api-recorded-execution",

        "incident_id":
            "api-recorded-incident",

        "action":
            "restart container",

        "target":
            "synthetic-container",

        "risk":
            "LOW",

        "rollback":
            "docker start synthetic-container",

        "status":
            "PENDING_APPROVAL",

        "created_at":
            "2026-09-17T00:00:00+00:00",

        "approved_by":
            None,

        "approved_at":
            None,
    }

    repository.save_action_request(
        approval
    )

    executor = ActionExecutorService(
        repository=repository,
        learning_repository=SimpleNamespace(
            save_learning=lambda record: None
        ),
    )

    executor.execution.docker.restart_container = (
        lambda target: {
            "status": "FAILED",
            "result": "verification failed",
            "evidence": [],
        }
    )

    monkeypatch.setattr(
        api,
        "_actions",
        repository,
    )

    monkeypatch.setattr(
        api,
        "_approval",
        ActionApprovalService(
            action_repository=repository,
            lifecycle_repository=SimpleNamespace(
                save=lambda event: event
            ),
        ),
    )

    monkeypatch.setattr(
        api,
        "_executor",
        executor,
    )


    app = FastAPI()
    app.include_router(
        api.router
    )

    with TestClient(app) as client:

        response = client.post(
            "/api/operator/actions/"
            + approval["id"]
            + "/approve",
            headers=AUTH_HEADERS,
        )


    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "FAILED"

    persisted = (
        repository.get_action_request(
            approval["id"]
        )
    )

    assert (
        persisted["approved_by"]
        == "ATLAS_WEB_OPERATOR"
    )

    assert (
        payload["execution_state"]["state"]
        == "EXECUTION_FAILED"
    )

    assert (
        payload[
            "execution_state"
        ][
            "history"
        ][
            "status"
        ]
        == "FAILED"
    )

    assert (
        payload[
            "execution_state"
        ][
            "history"
        ][
            "result"
        ]
        == "verification failed"
    )



@pytest.mark.parametrize(
    (
        "method",
        "path",
        "payload",
    ),
    [
        (
            "POST",
            "/api/operator/actions/propose",
            {
                "action":
                    "restart container",
                "target":
                    "synthetic-container",
            },
        ),
        (
            "GET",
            "/api/operator/actions/"
            "unknown-action",
            None,
        ),
        (
            "POST",
            "/api/operator/actions/"
            "unknown-action/approve",
            None,
        ),
        (
            "POST",
            "/api/operator/actions/"
            "unknown-action/reject",
            None,
        ),
    ],
)
def test_operator_endpoints_require_authentication(
    method,
    path,
    payload,
):

    from atlas.api import (
        operator_actions as api,
    )

    app = FastAPI()
    app.include_router(
        api.router
    )

    with TestClient(app) as client:

        response = client.request(
            method,
            path,
            json=payload,
        )

    assert response.status_code == 401

    assert (
        response.headers.get(
            "www-authenticate"
        )
        == "Bearer"
    )


def test_missing_server_token_fails_closed(
    monkeypatch,
):

    from atlas.api import (
        operator_actions as api,
    )

    monkeypatch.delenv(
        "ATLAS_OPERATOR_TOKEN",
        raising=False,
    )

    app = FastAPI()
    app.include_router(
        api.router
    )

    with TestClient(app) as client:

        response = client.get(
            "/api/operator/actions/"
            "unknown-action",
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 401


@pytest.mark.parametrize(
    "authorization",
    [
        "Basic abc",
        "Bearer",
        "Bearer wrong-token",
        "Something test-operator-token",
    ],
)
def test_invalid_operator_credentials_are_rejected(
    authorization,
):

    from atlas.api import (
        operator_actions as api,
    )

    app = FastAPI()
    app.include_router(
        api.router
    )

    with TestClient(app) as client:

        response = client.get(
            "/api/operator/actions/"
            "unknown-action",
            headers={
                "Authorization":
                    authorization,
            },
        )

    assert response.status_code == 401


def test_unauthorized_approval_never_reaches_operator_logic(
    monkeypatch,
):

    from atlas.api import (
        operator_actions as api,
    )

    class NeverActions:

        def get_action_request(
            self,
            action_id,
        ):

            raise AssertionError(
                "unauthorized request "
                "reached operator logic"
            )

    monkeypatch.setattr(
        api,
        "_actions",
        NeverActions(),
    )

    app = FastAPI()
    app.include_router(
        api.router
    )

    with TestClient(app) as client:

        response = client.post(
            "/api/operator/actions/"
            "forbidden/approve",
            headers={
                "Authorization":
                    "Bearer wrong-token",
            },
        )

    assert response.status_code == 401


def test_authenticated_reject_records_operator_identity(
    tmp_path,
    monkeypatch,
):

    from atlas.api import (
        operator_actions as api,
    )

    from atlas.services.intelligence.approval.service import (
        ActionApprovalService,
    )

    from atlas.storage.action_repository import (
        ActionRepository,
    )

    from atlas.storage.database import Database


    repository = ActionRepository(
        Database(
            tmp_path
            / "operator-reject-auth.db"
        )
    )

    action = {
        "id":
            "authenticated-reject",

        "incident_id":
            "authenticated-reject-incident",

        "action":
            "restart container",

        "target":
            "synthetic-container",

        "risk":
            "LOW",

        "rollback":
            "docker start synthetic-container",

        "status":
            "PENDING_APPROVAL",

        "created_at":
            "2026-09-17T00:00:00+00:00",

        "approved_by":
            None,

        "approved_at":
            None,
    }

    repository.save_action_request(
        action
    )

    monkeypatch.setattr(
        api,
        "_actions",
        repository,
    )

    monkeypatch.setattr(
        api,
        "_approval",
        ActionApprovalService(
            action_repository=repository,
            lifecycle_repository=SimpleNamespace(
                save=lambda event: event
            ),
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
            + "/reject",
            headers=AUTH_HEADERS,
        )


    assert response.status_code == 200

    persisted = (
        repository.get_action_request(
            action["id"]
        )
    )

    assert persisted["status"] == "REJECTED"

    assert (
        persisted["approved_by"]
        == "ATLAS_WEB_OPERATOR"
    )
