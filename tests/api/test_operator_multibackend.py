from fastapi import FastAPI
from fastapi.testclient import TestClient

from atlas.core.asset import (
    Asset,
    AssetType,
    Capability,
    Criticality,
    ServiceImportance,
)
from atlas.core.identity import AssetIdentity
from atlas.services.intelligence.policy.service import (
    ActionPolicyService,
)
from atlas.models.action import SafeAction


TOKEN = "operator-multibackend-token"

AUTH = {
    "Authorization":
        "Bearer " + TOKEN,
}


def safe_action(
    action,
    target,
):

    return SafeAction(
        action=action,
        target=target,
        incident_id="TEST",
        risk="LOW",
        requires_approval=True,
        rollback="manual",
        status="PENDING_APPROVAL",
    )


def test_policy_supports_systemd_capabilities():

    asset = Asset(
        id="service-asset",
        name="atlas-collector.service",
        type=AssetType.SERVICE,
        criticality=Criticality.MEDIUM,
        service_importance=(
            ServiceImportance.SYSTEM
        ),
        capabilities={
            Capability.START,
            Capability.STOP,
            Capability.RESTART,
        },
    )

    result = (
        ActionPolicyService()
        .evaluate(
            safe_action(
                "restart service",
                "atlas-collector.service",
            ),
            asset,
        )
    )

    assert result["status"] == "ALLOWED"

    assert (
        result["required_capability"]
        == "RESTART"
    )


def test_policy_blocks_disruptive_restart_of_protected_vm():

    asset = Asset(
        id="vm-300",
        name="atlas-windows",
        type=AssetType.VM,
        criticality=Criticality.HIGH,
        service_importance=(
            ServiceImportance.NORMAL
        ),
        capabilities={
            Capability.RESTART,
        },
    )

    result = (
        ActionPolicyService()
        .evaluate(
            safe_action(
                "restart vm",
                "300",
            ),
            asset,
        )
    )

    assert result["status"] == "BLOCKED"

    assert (
        "protected asset"
        in result["reason"]
    )


def test_policy_allows_start_of_protected_vm():

    asset = Asset(
        id="vm-300",
        name="atlas-windows",
        type=AssetType.VM,
        criticality=Criticality.HIGH,
        service_importance=(
            ServiceImportance.NORMAL
        ),
        capabilities={
            Capability.START,
        },
    )

    result = (
        ActionPolicyService()
        .evaluate(
            safe_action(
                "start vm",
                "300",
            ),
            asset,
        )
    )

    assert result["status"] == "ALLOWED"


class IdentityRepository:

    def __init__(
        self,
        asset,
    ):

        self.asset = asset
        self.identity = None

    def find_by_identity(
        self,
        identity,
    ):

        self.identity = identity
        return self.asset.id

    def get_asset(
        self,
        asset_id,
    ):

        assert (
            asset_id
            == self.asset.id
        )

        return self.asset


def test_operator_resolves_systemd_asset_identity(
    monkeypatch,
):

    from atlas.api import (
        operator_actions as api,
    )

    asset = Asset(
        id="service",
        name="atlas-collector.service",
        type=AssetType.SERVICE,
    )

    repository = IdentityRepository(
        asset
    )

    monkeypatch.setattr(
        api,
        "_asset_repository",
        repository,
    )

    monkeypatch.setattr(
        api.socket,
        "gethostname",
        lambda:
            "debian-docker",
    )

    resolved = (
        api._resolve_operator_asset(
            "atlas-collector.service",
            "restart service",
        )
    )

    assert resolved is asset

    assert repository.identity == (
        AssetIdentity(
            serial=(
                "debian-docker:"
                "atlas-collector.service"
            ),
            model="Systemd Service",
            vendor="Linux",
        )
    )


def test_operator_resolves_proxmox_vm_identity(
    monkeypatch,
):

    from atlas.api import (
        operator_actions as api,
    )

    asset = Asset(
        id="vm",
        name="atlas-windows",
        type=AssetType.VM,
    )

    repository = IdentityRepository(
        asset
    )

    monkeypatch.setattr(
        api,
        "_asset_repository",
        repository,
    )

    resolved = (
        api._resolve_operator_asset(
            "300",
            "start vm",
        )
    )

    assert resolved is asset

    assert repository.identity == (
        AssetIdentity(
            serial="300",
            model="Virtual Machine",
            vendor="Proxmox",
        )
    )


class CapturingApproval:

    def __init__(self):
        self.calls = []

    def request(
        self,
        action,
    ):

        self.calls.append(action)

        return {
            "id": "multi-request",
            "incident_id":
                action.incident_id,
            "action":
                action.action,
            "target":
                action.target,
            "risk":
                action.risk,
            "rollback":
                action.rollback,
            "status":
                "PENDING_APPROVAL",
            "approved_by": None,
            "approved_at": None,
        }


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
        return self.asset.id

    def get_asset(
        self,
        asset_id,
    ):
        return self.asset


def test_systemd_proposal_reaches_existing_approval_pipeline(
    monkeypatch,
):

    from atlas.api import (
        operator_actions as api,
    )

    asset = Asset(
        id="collector-service",
        name="atlas-collector.service",
        type=AssetType.SERVICE,
        criticality=Criticality.MEDIUM,
        service_importance=(
            ServiceImportance.SYSTEM
        ),
        capabilities={
            Capability.RESTART,
        },
    )

    approval = CapturingApproval()

    monkeypatch.setenv(
        "ATLAS_OPERATOR_TOKEN",
        TOKEN,
    )

    monkeypatch.setattr(
        api,
        "_asset_repository",
        FixedAssetRepository(
            asset
        ),
    )

    monkeypatch.setattr(
        api,
        "_approval",
        approval,
    )

    monkeypatch.setattr(
        api,
        "_validated_operator_target",
        lambda action, target: {
            "target":
                "atlas-collector.service",
            "state":
                "active",
        },
    )


    app = FastAPI()
    app.include_router(api.router)


    with TestClient(app) as client:

        response = client.post(
            "/api/operator/actions/propose",
            headers=AUTH,
            json={
                "action":
                    "restart service",

                "target":
                    "atlas-collector.service",
            },
        )


    assert response.status_code == 200

    payload = response.json()

    assert (
        payload["status"]
        == "PENDING_APPROVAL"
    )

    assert (
        payload["target_state"]
        == "ACTIVE"
    )

    assert len(
        approval.calls
    ) == 1


def test_unrouted_lxc_stop_is_rejected_by_operator_api(
    monkeypatch,
):

    from atlas.api import (
        operator_actions as api,
    )

    monkeypatch.setenv(
        "ATLAS_OPERATOR_TOKEN",
        TOKEN,
    )

    app = FastAPI()
    app.include_router(api.router)


    with TestClient(app) as client:

        response = client.post(
            "/api/operator/actions/propose",
            headers=AUTH,
            json={
                "action":
                    "stop lxc",

                "target":
                    "103",
            },
        )


    assert response.status_code == 400


def test_multibackend_ui_routes_only_governed_operator_actions():

    from pathlib import Path

    root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    source = (
        root
        / "src/atlas/api/static/js/atlas.js"
    ).read_text()

    for action in (
        "start service",
        "restart service",
        "stop service",
        "start vm",
        "restart vm",
        "stop vm",
        "restart lxc",
        "start container",
        "restart container",
        "stop container",
    ):
        assert action in source

    parser = source[
        source.index(
            "function parseOperatorCommand"
        ):
        source.index(
            "function escapeOperatorHTML"
        )
    ]

    for forbidden in (
        "systemctl",
        "docker restart",
        "qm ",
        "pct ",
        "subprocess",
    ):
        assert forbidden not in parser
