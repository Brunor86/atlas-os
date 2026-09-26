from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from atlas.api.operator_actions import (
    _SUPPORTED_OPERATOR_ACTIONS,
    _evaluate_operator_policy,
    _validate_operator_transition,
)

from atlas.core.asset import (
    Asset,
    AssetType,
    Capability,
    Criticality,
    ServiceImportance,
)

from atlas.models.action import (
    SafeAction,
)

from atlas.services.intelligence.policy.service import (
    ActionPolicyService,
)

from atlas.services.intelligence.execution.handlers.proxmox import (
    ProxmoxActionHandler,
)

from atlas.services.intelligence.execution.service import (
    ActionExecutionService,
)

from atlas.services.intelligence.execution.validators import (
    ActionValidator,
)

from atlas.services.intelligence.verification.service import (
    ActionVerificationService,
)


class FakeLxcLifecycleProxmox:

    def __init__(
        self,
        *,
        status,
        task_exitstatus="OK",
        post_error=None,
    ):
        self.status = status
        self.task_exitstatus = task_exitstatus
        self.post_error = post_error

        self.posts = []
        self.gets = []
        self.expected_types = []


    def resolve_guest(
        self,
        vmid,
        expected_type=None,
    ):

        self.expected_types.append(
            expected_type
        )

        return SimpleNamespace(
            vmid=int(
                vmid
            ),
            node="atlas",
            type="lxc",
            status=self.status,
            name="olivasat",
        )


    def _post(
        self,
        endpoint,
        data=None,
    ):

        if self.post_error:
            raise RuntimeError(
                self.post_error
            )

        self.posts.append(
            endpoint
        )

        if endpoint.endswith(
            "/status/start"
        ):
            self.status = "running"

        elif endpoint.endswith(
            "/status/stop"
        ):
            self.status = "stopped"

        return (
            "UPID:atlas:"
            "00000099:"
            "lxc-operation"
        )


    def _get(
        self,
        endpoint,
    ):

        self.gets.append(
            endpoint
        )

        return {
            "status":
                "stopped",

            "exitstatus":
                self.task_exitstatus,
        }


def handler(
    fake,
    *,
    allowed=None,
):

    return ProxmoxActionHandler(
        proxmox=fake,
        poll_attempts=2,
        poll_interval=0,
        allowed_qemu_vmids={300},
        allowed_lxc_vmids=(
            {103}
            if allowed is None
            else allowed
        ),
    )


def test_lxc_start_stop_are_full_operator_capabilities():

    allowed = set(
        ActionValidator.ALLOWED_ACTIONS
    )

    assert "start lxc" in allowed
    assert "restart lxc" in allowed
    assert "stop lxc" in allowed

    assert (
        "start lxc"
        in _SUPPORTED_OPERATOR_ACTIONS
    )

    assert (
        "stop lxc"
        in _SUPPORTED_OPERATOR_ACTIONS
    )

    assert (
        ActionExecutionService
        .is_action_executable(
            "start lxc"
        )
    )

    assert (
        ActionExecutionService
        .is_action_executable(
            "restart lxc"
        )
    )

    assert (
        ActionExecutionService
        .is_action_executable(
            "stop lxc"
        )
    )


def test_start_lxc_posts_and_verifies_running_state():

    fake = FakeLxcLifecycleProxmox(
        status="stopped"
    )

    result = (
        handler(fake)
        .start_lxc(
            "103"
        )
    )

    assert result["status"] == "SUCCESS"

    assert result["result"] == (
        "LXC 103 running"
    )

    assert fake.posts == [
        (
            "/api2/json/nodes/"
            "atlas/lxc/103/"
            "status/start"
        )
    ]

    assert any(
        "/tasks/"
        in endpoint
        for endpoint
        in fake.gets
    )

    assert (
        "verified_state=running"
        in result["evidence"]
    )

    assert all(
        value == "lxc"
        for value
        in fake.expected_types
    )


def test_stop_lxc_posts_and_verifies_stopped_state():

    fake = FakeLxcLifecycleProxmox(
        status="running"
    )

    result = (
        handler(fake)
        .stop_lxc(
            "103"
        )
    )

    assert result["status"] == "SUCCESS"

    assert result["result"] == (
        "LXC 103 stopped"
    )

    assert fake.posts == [
        (
            "/api2/json/nodes/"
            "atlas/lxc/103/"
            "status/stop"
        )
    ]

    assert any(
        "/tasks/"
        in endpoint
        for endpoint
        in fake.gets
    )

    assert (
        "verified_state=stopped"
        in result["evidence"]
    )


def test_start_lxc_rejects_running_guest_without_post():

    fake = FakeLxcLifecycleProxmox(
        status="running"
    )

    result = (
        handler(fake)
        .start_lxc(
            "103"
        )
    )

    assert result["status"] == "FAILED"

    assert (
        "already running"
        in result["result"]
    )

    assert fake.posts == []


def test_stop_lxc_rejects_stopped_guest_without_post():

    fake = FakeLxcLifecycleProxmox(
        status="stopped"
    )

    result = (
        handler(fake)
        .stop_lxc(
            "103"
        )
    )

    assert result["status"] == "FAILED"

    assert (
        "already stopped"
        in result["result"]
    )

    assert fake.posts == []


@pytest.mark.parametrize(
    (
        "operation",
        "initial_state",
    ),
    [
        (
            "start_lxc",
            "stopped",
        ),
        (
            "stop_lxc",
            "running",
        ),
    ],
)
def test_non_allowlisted_lxc_never_posts(
    operation,
    initial_state,
):

    fake = FakeLxcLifecycleProxmox(
        status=initial_state
    )

    instance = handler(
        fake,
        allowed=set(),
    )

    result = getattr(
        instance,
        operation,
    )(
        "103"
    )

    assert result["status"] == "FAILED"

    assert (
        "not allowed"
        in result["result"]
    )

    assert fake.posts == []


@pytest.mark.parametrize(
    (
        "operation",
        "initial_state",
    ),
    [
        (
            "start_lxc",
            "stopped",
        ),
        (
            "stop_lxc",
            "running",
        ),
    ],
)
def test_failed_proxmox_task_never_reports_success(
    operation,
    initial_state,
):

    fake = FakeLxcLifecycleProxmox(
        status=initial_state,
        task_exitstatus="ERROR",
    )

    result = getattr(
        handler(fake),
        operation,
    )(
        "103"
    )

    assert result["status"] == "FAILED"

    assert (
        "task failed"
        in result["result"]
    )


def test_lxc_verification_routes_are_independent():

    class FakeState:

        def __init__(
            self,
            status,
        ):
            self.status = status


    class FakeProxmox:

        def __init__(
            self,
            status,
        ):
            self.status = status
            self.calls = []


        def resolve_guest(
            self,
            vmid,
            expected_type=None,
        ):

            self.calls.append(
                (
                    vmid,
                    expected_type,
                )
            )

            return FakeState(
                self.status
            )


    running = FakeProxmox(
        "running"
    )

    start_result = (
        ActionVerificationService(
            proxmox=running
        )
        .verify(
            "start lxc",
            "103",
        )
    )

    assert (
        start_result["status"]
        == "VERIFIED"
    )

    assert (
        start_result[
            "expected_state"
        ]
        == "running"
    )

    assert running.calls == [
        (
            103,
            "lxc",
        )
    ]


    stopped = FakeProxmox(
        "stopped"
    )

    stop_result = (
        ActionVerificationService(
            proxmox=stopped
        )
        .verify(
            "stop lxc",
            "103",
        )
    )

    assert (
        stop_result["status"]
        == "VERIFIED"
    )

    assert (
        stop_result[
            "expected_state"
        ]
        == "stopped"
    )

    assert stopped.calls == [
        (
            103,
            "lxc",
        )
    ]


def test_operator_transition_contract_for_lxc():

    _validate_operator_transition(
        "start lxc",
        "103",
        "stopped",
    )

    _validate_operator_transition(
        "stop lxc",
        "103",
        "running",
    )


    with pytest.raises(
        HTTPException
    ):
        _validate_operator_transition(
            "start lxc",
            "103",
            "running",
        )


    with pytest.raises(
        HTTPException
    ):
        _validate_operator_transition(
            "stop lxc",
            "103",
            "stopped",
        )



def make_lxc_policy_asset(
    *,
    vmid="103",
    criticality=Criticality.HIGH,
    importance=ServiceImportance.SYSTEM,
):

    return Asset(
        id=(
            "lxc-proxmox-"
            "linux_container-"
            + str(vmid)
        ),
        name="olivasat",
        type=AssetType.LXC,
        criticality=criticality,
        service_importance=importance,
        capabilities={
            Capability.START,
            Capability.STOP,
            Capability.RESTART,
            Capability.SNAPSHOT,
        },
    )


def test_generic_policy_knows_lxc_start_and_stop():

    policy = ActionPolicyService()

    asset = make_lxc_policy_asset()


    start = policy.evaluate(
        SafeAction(
            action="start lxc",
            target="103",
            requires_approval=True,
        ),
        asset,
    )

    assert (
        start["status"]
        == "ALLOWED"
    )


    stop = policy.evaluate(
        SafeAction(
            action="stop lxc",
            target="103",
            requires_approval=True,
        ),
        asset,
    )

    assert (
        stop["status"]
        == "BLOCKED"
    )

    assert (
        stop["reason"]
        == (
            "disruptive action is blocked "
            "for protected asset"
        )
    )


class FixedLxcPolicyRepository:

    def __init__(
        self,
        asset,
    ):
        self.asset = asset


    def find_by_identity(
        self,
        identity,
    ):

        if (
            identity.serial
            != self.asset.identity.serial
        ):
            return None

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


def test_operator_policy_allows_allowlisted_high_lxc_stop(
    monkeypatch,
):

    from atlas.api import (
        operator_actions as api,
    )

    asset = make_lxc_policy_asset()

    asset.identity.serial = "103"
    asset.identity.model = "Linux Container"
    asset.identity.vendor = "Proxmox"


    monkeypatch.setattr(
        api,
        "_asset_repository",
        FixedLxcPolicyRepository(
            asset
        ),
    )

    monkeypatch.setattr(
        api,
        "get_executable_lxc_vmids",
        lambda:
            {103},
    )


    result = (
        _evaluate_operator_policy(
            SafeAction(
                action="stop lxc",
                target="103",
                risk="HIGH",
                requires_approval=True,
            )
        )
    )


    assert (
        result["status"]
        == "ALLOWED"
    )

    assert (
        result[
            "protected_override"
        ]
        is True
    )

    assert (
        result[
            "authorization"
        ]
        == "ATLAS_OPERATOR_LXC_VMIDS"
    )

    assert (
        result[
            "human_approval_required"
        ]
        is True
    )


def test_operator_policy_blocks_non_allowlisted_lxc_before_execution(
    monkeypatch,
):

    from atlas.api import (
        operator_actions as api,
    )

    asset = make_lxc_policy_asset(
        vmid="102"
    )

    asset.identity.serial = "102"
    asset.identity.model = "Linux Container"
    asset.identity.vendor = "Proxmox"


    monkeypatch.setattr(
        api,
        "_asset_repository",
        FixedLxcPolicyRepository(
            asset
        ),
    )

    monkeypatch.setattr(
        api,
        "get_executable_lxc_vmids",
        lambda:
            {103},
    )


    result = (
        _evaluate_operator_policy(
            SafeAction(
                action="start lxc",
                target="102",
                requires_approval=True,
            )
        )
    )


    assert (
        result["status"]
        == "BLOCKED"
    )

    assert (
        "not enabled for operator execution"
        in result["reason"]
    )


def test_operator_policy_never_overrides_critical_lxc_stop(
    monkeypatch,
):

    from atlas.api import (
        operator_actions as api,
    )

    asset = make_lxc_policy_asset(
        criticality=Criticality.CRITICAL,
    )

    asset.identity.serial = "103"
    asset.identity.model = "Linux Container"
    asset.identity.vendor = "Proxmox"


    monkeypatch.setattr(
        api,
        "_asset_repository",
        FixedLxcPolicyRepository(
            asset
        ),
    )

    monkeypatch.setattr(
        api,
        "get_executable_lxc_vmids",
        lambda:
            {103},
    )


    result = (
        _evaluate_operator_policy(
            SafeAction(
                action="stop lxc",
                target="103",
                risk="HIGH",
                requires_approval=True,
            )
        )
    )


    assert (
        result["status"]
        == "BLOCKED"
    )

    assert (
        "protected asset"
        in result["reason"]
    )
