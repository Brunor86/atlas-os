from fastapi import FastAPI
from fastapi.testclient import TestClient

from atlas.core.asset import (
    Asset,
    AssetType,
    Capability,
    Criticality,
    ServiceImportance,
)


TOKEN = "operator-policy-test-token"

AUTH = {
    "Authorization":
        f"Bearer {TOKEN}",
}


class NeverApproval:

    def request(
        self,
        safe_action,
    ):

        raise AssertionError(
            "blocked policy reached approval"
        )


class MissingAssetRepository:

    def find_by_identity(
        self,
        identity,
    ):

        return None


class FixedAssetRepository:

    def __init__(
        self,
        asset,
    ):

        self.asset = asset

    def find_by_identity(
        self,
        identity,
    ):

        assert identity.serial == (
            self.asset.name
        )

        assert identity.vendor == "Docker"

        return self.asset.id

    def get_asset(
        self,
        asset_id,
    ):

        assert asset_id == self.asset.id

        return self.asset


def make_app(
    monkeypatch,
    repository,
):

    from atlas.api import (
        operator_actions as api,
    )

    monkeypatch.setenv(
        "ATLAS_OPERATOR_TOKEN",
        TOKEN,
    )

    monkeypatch.setattr(
        api,
        "_asset_repository",
        repository,
    )

    monkeypatch.setattr(
        api,
        "_approval",
        NeverApproval(),
    )

    monkeypatch.setattr(
        api,
        "_validated_container_name",
        lambda value:
            str(value),
    )

    monkeypatch.setattr(
        api,
        "_container_running",
        lambda target:
            True,
    )

    app = FastAPI()

    app.include_router(
        api.router
    )

    return app


def test_unregistered_container_is_blocked_before_approval(
    monkeypatch,
):

    app = make_app(
        monkeypatch,
        MissingAssetRepository(),
    )

    with TestClient(app) as client:

        response = client.post(
            "/api/operator/actions/propose",
            headers=AUTH,
            json={
                "action":
                    "restart container",

                "target":
                    "test-container",
            },
        )

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "BLOCKED"

    assert (
        payload["policy"]["status"]
        == "BLOCKED"
    )

    assert (
        "not registered"
        in payload[
            "policy"
        ][
            "reason"
        ]
    )


def test_protected_restart_is_blocked_before_approval(
    monkeypatch,
):

    asset = Asset(
        id="protected-container",
        name="test-container",
        type=AssetType.APPLICATION,
        criticality=Criticality.HIGH,
        service_importance=(
            ServiceImportance.NORMAL
        ),
        capabilities={
            Capability.RESTART,
        },
    )

    app = make_app(
        monkeypatch,
        FixedAssetRepository(
            asset
        ),
    )

    with TestClient(app) as client:

        response = client.post(
            "/api/operator/actions/propose",
            headers=AUTH,
            json={
                "action":
                    "restart container",

                "target":
                    "test-container",
            },
        )

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "BLOCKED"

    assert (
        payload[
            "policy"
        ][
            "criticality"
        ]
        == "HIGH"
    )


class CapturingApproval:

    def __init__(
        self,
    ):

        self.calls = []


    def request(
        self,
        safe_action,
    ):

        self.calls.append(
            safe_action
        )

        return {
            "id":
                "policy-approved-request",

            "incident_id":
                safe_action.incident_id,

            "action":
                safe_action.action,

            "target":
                safe_action.target,

            "risk":
                safe_action.risk,

            "rollback":
                safe_action.rollback,

            "status":
                "PENDING_APPROVAL",

            "approved_by":
                None,

            "approved_at":
                None,
        }


def test_allowed_container_reaches_approval(
    monkeypatch,
):

    asset = Asset(
        id="allowed-container",
        name="test-container",
        type=AssetType.APPLICATION,
        criticality=Criticality.MEDIUM,
        service_importance=(
            ServiceImportance.NORMAL
        ),
        capabilities={
            Capability.RESTART,
        },
    )

    approval = CapturingApproval()

    app = make_app(
        monkeypatch,
        FixedAssetRepository(
            asset
        ),
    )

    from atlas.api import (
        operator_actions as api,
    )

    monkeypatch.setattr(
        api,
        "_approval",
        approval,
    )


    with TestClient(app) as client:

        response = client.post(
            "/api/operator/actions/propose",
            headers=AUTH,
            json={
                "action":
                    "restart container",

                "target":
                    "test-container",
            },
        )


    assert response.status_code == 200

    payload = response.json()

    assert (
        payload["status"]
        == "PENDING_APPROVAL"
    )

    assert (
        payload["policy"]["status"]
        == "ALLOWED"
    )

    assert len(
        approval.calls
    ) == 1


def test_policy_is_revalidated_before_approval(
    tmp_path,
    monkeypatch,
):

    from atlas.api import (
        operator_actions as api,
    )

    from atlas.storage.action_repository import (
        ActionRepository,
    )

    from atlas.storage.database import Database


    repository = ActionRepository(
        Database(
            tmp_path
            / "jit-policy.db"
        )
    )

    action = {
        "id":
            "jit-policy-action",

        "incident_id":
            "jit-policy-incident",

        "action":
            "restart container",

        "target":
            "test-container",

        "risk":
            "LOW",

        "rollback":
            "docker start test-container",

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


    protected_asset = Asset(
        id="protected-container",
        name="test-container",
        type=AssetType.APPLICATION,
        criticality=Criticality.HIGH,
        service_importance=(
            ServiceImportance.NORMAL
        ),
        capabilities={
            Capability.RESTART,
        },
    )


    from atlas.services.intelligence.approval.service import (
        ActionApprovalService,
    )


    class NeverExecute:

        def execute(
            self,
            *args,
            **kwargs,
        ):

            raise AssertionError(
                "blocked policy reached executor"
            )


    monkeypatch.setenv(
        "ATLAS_OPERATOR_TOKEN",
        TOKEN,
    )

    monkeypatch.setattr(
        api,
        "_actions",
        repository,
    )

    monkeypatch.setattr(
        api,
        "_asset_repository",
        FixedAssetRepository(
            protected_asset
        ),
    )

    monkeypatch.setattr(
        api,
        "_approval",
        ActionApprovalService(
            action_repository=repository,
            lifecycle_repository=type(
                "Lifecycle",
                (),
                {
                    "save":
                        lambda self, event:
                            event,
                },
            )(),
        ),
    )

    monkeypatch.setattr(
        api,
        "_executor",
        NeverExecute(),
    )


    app = FastAPI()
    app.include_router(
        api.router
    )


    with TestClient(app) as client:

        response = client.post(
            "/api/operator/actions/"
            + action["id"]
            + "/approve",
            headers=AUTH,
        )


    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "BLOCKED"

    assert (
        payload["policy"]["status"]
        == "BLOCKED"
    )

    assert (
        payload["policy"]["criticality"]
        == "HIGH"
    )

    assert (
        payload["execution"]["status"]
        == "BLOCKED"
    )

    persisted = (
        repository.get_action_request(
            action["id"]
        )
    )

    assert (
        persisted["status"]
        == "REJECTED"
    )

    assert (
        persisted["approved_by"]
        == "ATLAS_POLICY"
    )

    assert (
        repository.get_action_history()
        == []
    )

    assert (
        payload[
            "execution_state"
        ][
            "state"
        ]
        == "NOT_READY"
    )


    with TestClient(app) as client:

        second = client.post(
            "/api/operator/actions/"
            + action["id"]
            + "/approve",
            headers=AUTH,
        )


    assert second.status_code == 409
