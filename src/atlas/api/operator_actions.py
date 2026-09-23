from __future__ import annotations

import os
import re
import secrets
import socket
import subprocess
from types import SimpleNamespace
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request

from atlas.core.identity import AssetIdentity
from atlas.models.action import SafeAction
from atlas.services.intelligence.approval.service import (
    ActionApprovalService,
)
from atlas.services.intelligence.executor.service import (
    ActionExecutorService,
)
from atlas.services.intelligence.safety.service import (
    ActionSafetyService,
)
from atlas.services.intelligence.recovery.service import (
    ActionRecoveryService,
)
from atlas.services.intelligence.policy.service import (
    ActionPolicyService,
)
from atlas.config.operator import (
    get_executable_systemd_services,
    get_executable_qemu_vmids,
    get_executable_lxc_vmids,
)
from atlas.services.proxmox import (
    ProxmoxService,
)
from atlas.storage.action_repository import ActionRepository
from atlas.storage.asset_repository import AssetRepository
from atlas.storage.database import Database


router = APIRouter(
    prefix="/api/operator",
    tags=["operator"],
)


_TARGET_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$"
)

_SYSTEMD_TARGET_RE = re.compile(
    r"^[A-Za-z0-9]"
    r"[A-Za-z0-9_.@:-]{0,127}"
    r"\.service$"
)

_VMID_RE = re.compile(
    r"^[1-9][0-9]{0,8}$"
)


_SUPPORTED_OPERATOR_ACTIONS = {
    "start container",
    "restart container",
    "stop container",

    "start service",
    "restart service",
    "stop service",

    "start vm",
    "restart vm",
    "stop vm",

    "restart lxc",
}


_OPERATOR_TOKEN_ENV = (
    "ATLAS_OPERATOR_TOKEN"
)

_OPERATOR_IDENTITY = (
    "ATLAS_WEB_OPERATOR"
)


def _authenticate_operator(
    request: Request,
) -> str:

    expected = str(
        os.getenv(
            _OPERATOR_TOKEN_ENV,
            "",
        )
        or ""
    ).strip()

    authorization = str(
        request.headers.get(
            "Authorization",
            "",
        )
        or ""
    ).strip()

    scheme, separator, supplied = (
        authorization.partition(" ")
    )

    supplied = supplied.strip()

    valid = (
        bool(expected)
        and separator == " "
        and scheme.lower() == "bearer"
        and bool(supplied)
        and secrets.compare_digest(
            supplied,
            expected,
        )
    )

    if not valid:
        raise HTTPException(
            status_code=401,
            detail=(
                "operator authentication required"
            ),
            headers={
                "WWW-Authenticate":
                    "Bearer",
            },
        )

    return _OPERATOR_IDENTITY


class _OperatorLifecycleRepository:

    def save(
        self,
        event,
    ):
        return event


class _OperatorLearningRepository:

    def save_learning(
        self,
        record,
    ):
        return record

    def save_learning_record(
        self,
        record,
    ):
        return record


_database = Database()

_actions = ActionRepository(
    _database
)

_approval = ActionApprovalService(
    action_repository=_actions,
    lifecycle_repository=(
        _OperatorLifecycleRepository()
    ),
)

_executor = ActionExecutorService(
    repository=_actions,
    learning_repository=(
        _OperatorLearningRepository()
    ),
)

_recovery = ActionRecoveryService(
    repository=_actions,
)

_safety = ActionSafetyService()

_policy = ActionPolicyService()

_asset_repository = AssetRepository()


def _operator_asset_identity(
    action: str,
    target: str,
):

    normalized = str(
        action
        or ""
    ).strip().lower()

    target = str(
        target
        or ""
    ).strip()


    if normalized.endswith(
        "container"
    ):

        return AssetIdentity(
            serial=target,
            vendor="Docker",
        )


    if normalized.endswith(
        "service"
    ):

        return AssetIdentity(
            serial=(
                socket.gethostname()
                + ":"
                + target
            ),
            model="Systemd Service",
            vendor="Linux",
        )


    if normalized.endswith(
        "vm"
    ):

        return AssetIdentity(
            serial=target,
            model="Virtual Machine",
            vendor="Proxmox",
        )


    if normalized.endswith(
        "lxc"
    ):

        return AssetIdentity(
            serial=target,
            model="Linux Container",
            vendor="Proxmox",
        )


    return None


def _resolve_operator_asset(
    target: str,
    action: str = "",
):

    identity = (
        _operator_asset_identity(
            action,
            target,
        )
    )

    if identity is None:
        return None


    asset_id = (
        _asset_repository
        .find_by_identity(
            identity
        )
    )

    if not asset_id:
        return None

    return _asset_repository.get_asset(
        asset_id
    )


def _evaluate_operator_policy(
    safe_action,
) -> dict:

    target = str(
        getattr(
            safe_action,
            "target",
            "",
        )
        or ""
    ).strip()

    asset = _resolve_operator_asset(
        target,
        safe_action.action,
    )

    return _policy.evaluate(
        safe_action,
        asset,
    )


def _validated_container_name(
    value,
) -> str:

    target = str(
        value or ""
    ).strip()

    if not target:
        raise HTTPException(
            status_code=400,
            detail="target is required",
        )

    if not _TARGET_RE.fullmatch(
        target
    ):
        raise HTTPException(
            status_code=400,
            detail="invalid container target",
        )

    inspect = subprocess.run(
        [
            "docker",
            "inspect",
            "--type",
            "container",
            "-f",
            "{{.Name}}",
            target,
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    if inspect.returncode != 0:
        raise HTTPException(
            status_code=404,
            detail=(
                "Docker container not found: "
                + target
            ),
        )

    canonical = (
        inspect.stdout
        .strip()
        .lstrip("/")
    )

    if canonical != target:
        raise HTTPException(
            status_code=400,
            detail=(
                "target must be the canonical "
                "container name"
            ),
        )

    return canonical


def _container_running(
    target: str,
) -> bool:

    inspect = subprocess.run(
        [
            "docker",
            "inspect",
            "-f",
            "{{.State.Running}}",
            target,
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    if inspect.returncode != 0:
        raise HTTPException(
            status_code=404,
            detail=(
                "Docker container not found: "
                + target
            ),
        )

    return (
        inspect.stdout.strip().lower()
        == "true"
    )


def _systemd_property(
    target: str,
    property_name: str,
) -> str:

    result = subprocess.run(
        [
            "systemctl",
            "show",
            target,
            "--property="
            + property_name,
            "--value",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    if result.returncode != 0:

        raise HTTPException(
            status_code=404,
            detail=(
                "systemd service "
                "inspection failed: "
                + target
            ),
        )

    return (
        result.stdout
        .strip()
    )


def _validated_systemd_target(
    value,
):

    target = str(
        value
        or ""
    ).strip()


    if not _SYSTEMD_TARGET_RE.fullmatch(
        target
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "invalid systemd "
                "service target"
            ),
        )


    if (
        target
        not in get_executable_systemd_services()
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "systemd execution "
                "is not enabled for "
                + target
            ),
        )


    canonical = _systemd_property(
        target,
        "Id",
    )

    load_state = _systemd_property(
        target,
        "LoadState",
    )

    active_state = _systemd_property(
        target,
        "ActiveState",
    )


    if canonical != target:

        raise HTTPException(
            status_code=400,
            detail=(
                "target must be the "
                "canonical systemd "
                "service name"
            ),
        )


    if load_state != "loaded":

        raise HTTPException(
            status_code=409,
            detail=(
                "systemd service is "
                "not loaded"
            ),
        )


    return (
        canonical,
        active_state.lower()
        or "unknown",
    )


def _validated_proxmox_target(
    value,
    *,
    guest_type,
):

    raw = str(
        value
        or ""
    ).strip()


    if not _VMID_RE.fullmatch(
        raw
    ):

        raise HTTPException(
            status_code=400,
            detail="invalid Proxmox VMID",
        )


    vmid = int(raw)


    if (
        guest_type == "qemu"
        and vmid
        not in get_executable_qemu_vmids()
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "Proxmox execution "
                "is not enabled for "
                "VMID "
                + str(vmid)
            ),
        )


    if (
        guest_type == "lxc"
        and vmid
        not in get_executable_lxc_vmids()
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "Proxmox execution "
                "is not enabled for "
                "LXC "
                + str(vmid)
            ),
        )


    try:

        guest = (
            ProxmoxService()
            .resolve_guest(
                vmid,
                expected_type=guest_type,
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


    return (
        str(vmid),
        str(
            guest.status
            or "unknown"
        ).lower(),
    )


def _validated_operator_target(
    action: str,
    value,
):

    normalized = str(
        action
        or ""
    ).strip().lower()


    if normalized.endswith(
        "container"
    ):

        target = (
            _validated_container_name(
                value
            )
        )

        state = (
            "running"
            if _container_running(
                target
            )
            else "stopped"
        )


    elif normalized.endswith(
        "service"
    ):

        target, state = (
            _validated_systemd_target(
                value
            )
        )


    elif normalized.endswith(
        "vm"
    ):

        target, state = (
            _validated_proxmox_target(
                value,
                guest_type="qemu",
            )
        )


    elif normalized.endswith(
        "lxc"
    ):

        target, state = (
            _validated_proxmox_target(
                value,
                guest_type="lxc",
            )
        )


    else:

        raise HTTPException(
            status_code=400,
            detail="unsupported operator backend",
        )


    return {
        "target": target,
        "state": state,
    }


def _validate_operator_transition(
    action: str,
    target: str,
    state: str,
):

    normalized = str(
        action
        or ""
    ).strip().lower()

    state = str(
        state
        or "unknown"
    ).strip().lower()


    start_actions = {
        "start container",
        "start service",
        "start vm",
    }

    running_required = {
        "restart container",
        "stop container",

        "restart service",
        "stop service",

        "restart vm",
        "stop vm",

        "restart lxc",
    }


    if (
        normalized
        in start_actions
    ):

        already_running = (
            state == "running"
            if normalized.endswith(
                ("container", "vm")
            )
            else state == "active"
        )

        if already_running:

            raise HTTPException(
                status_code=409,
                detail=(
                    target
                    + " is already running"
                ),
            )


    if (
        normalized
        in running_required
    ):

        expected = (
            "active"
            if normalized.endswith(
                "service"
            )
            else "running"
        )

        if state != expected:

            raise HTTPException(
                status_code=409,
                detail=(
                    target
                    + " is not "
                    + expected
                    + "; current state="
                    + state
                ),
            )


def _execution_dict(
    execution,
):

    if isinstance(
        execution,
        dict,
    ):
        return dict(
            execution
        )

    values = getattr(
        execution,
        "__dict__",
        None,
    )

    if isinstance(
        values,
        dict,
    ):
        return dict(
            values
        )

    return {
        "status": "FAILED",
        "result": str(
            execution
        ),
    }


@router.post(
    "/actions/propose"
)
async def propose_action(
    request: Request,
    operator_user: str = Depends(
        _authenticate_operator
    ),
):

    payload = await request.json()

    action = str(
        payload.get(
            "action",
            "",
        )
        or ""
    ).strip().lower()

    if (
        action
        not in _SUPPORTED_OPERATOR_ACTIONS
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "unsupported operator action"
            ),
        )


    target_profile = (
        _validated_operator_target(
            action,
            payload.get(
                "target"
            ),
        )
    )

    target = (
        target_profile["target"]
    )

    target_state = (
        target_profile["state"]
    )


    _validate_operator_transition(
        action,
        target,
        target_state,
    )


    operation_id = (
        "OP-"
        + str(uuid4())
    )

    safety_incident = SimpleNamespace(
        incident_id=operation_id,
        asset=target,
        diagnosis={},
        recommendation={
            "action":
                action,

            "incident_id":
                operation_id,

            "evidence": [
                {
                    "source":
                        "operator-api",

                    "type":
                        "operator-request",

                    "target":
                        target,
                }
            ],
        },
    )

    safety = _safety.evaluate(
        safety_incident
    )

    if (
        safety.get(
            "status"
        )
        == "BLOCKED"
    ):
        return {
            "status": "BLOCKED",
            "safety": safety,
        }

    safe_action = SafeAction(
        action=safety.get(
            "action",
            "",
        ),
        target=safety.get(
            "target",
            target,
        ),
        incident_id=operation_id,
        risk=safety.get(
            "risk",
            "UNKNOWN",
        ),
        requires_approval=bool(
            safety.get(
                "requires_approval",
                True,
            )
        ),
        rollback=safety.get(
            "rollback",
            "",
        ),
        status=safety.get(
            "status",
            "PENDING_APPROVAL",
        ),
        evidence=safety.get(
            "evidence",
            [],
        ),
    )


    policy = _evaluate_operator_policy(
        safe_action
    )

    if (
        policy.get(
            "status"
        )
        != "ALLOWED"
    ):

        return {
            "status":
                "BLOCKED",

            "safety":
                safety,

            "policy":
                policy,
        }


    action_request = (
        _approval.request(
            safe_action
        )
    )

    return {
        "status":
            "PENDING_APPROVAL",

        "action_request":
            action_request,

        "safety": {
            "validated": True,
            "risk":
                safe_action.risk,
        },

        "policy":
            policy,

        "target_state":
            str(
                target_state
                or "unknown"
            ).upper(),
    }


def _operator_display_state(
    action,
    execution_state,
) -> str:

    raw_status = str(
        action.get(
            "status",
            "",
        )
        or ""
    ).strip().upper()

    execution_status = str(
        (
            execution_state
            or {}
        ).get(
            "state",
            "",
        )
        or ""
    ).strip().upper()


    if (
        execution_status
        and execution_status
        != "NOT_READY"
    ):
        return execution_status


    if raw_status:
        return raw_status


    return "UNKNOWN"


@router.get(
    "/actions"
)
def list_actions(
    limit: int = 50,
    state: str | None = None,
    operator_user: str = Depends(
        _authenticate_operator
    ),
):

    safe_limit = max(
        1,
        min(
            int(limit or 50),
            100,
        ),
    )

    requested_state = str(
        state
        or ""
    ).strip().upper()

    actions = (
        _actions.list_action_requests(
            limit=safe_limit
        )
    )

    items = []
    summary = {}


    for action in actions:

        execution_state = (
            _actions
            .get_action_execution_state(
                action["id"]
            )
            or {}
        )

        display_state = (
            _operator_display_state(
                action,
                execution_state,
            )
        )

        summary[
            display_state
        ] = (
            summary.get(
                display_state,
                0,
            )
            + 1
        )


        if (
            requested_state
            and requested_state != "ALL"
            and display_state
            != requested_state
        ):
            continue


        items.append(
            {
                "id":
                    action["id"],

                "state":
                    display_state,

                "action_request":
                    action,

                "execution_state":
                    execution_state,
            }
        )


    return {
        "status": "SUCCESS",
        "actions": items,
        "summary": summary,
        "window_total": len(actions),
        "returned": len(items),
    }


@router.get(
    "/actions/{action_id}"
)
def get_action(
    action_id: str,
    operator_user: str = Depends(
        _authenticate_operator
    ),
):

    action = (
        _actions.get_action_request(
            action_id
        )
    )

    if not action:
        raise HTTPException(
            status_code=404,
            detail="action request not found",
        )

    execution_state = (
        _actions.get_action_execution_state(
            action_id
        )
    )

    return {
        "status": "SUCCESS",
        "action_request": action,
        "execution_state": execution_state,
        "verification_history": (
            _actions
            .get_action_verification_history(
                action_id
            )
        ),
    }


@router.post(
    "/actions/{action_id}/approve"
)
def approve_action(
    action_id: str,
    operator_user: str = Depends(
        _authenticate_operator
    ),
):

    current = (
        _actions.get_action_request(
            action_id
        )
    )

    if not current:
        raise HTTPException(
            status_code=404,
            detail="action request not found",
        )

    if (
        current.get("status")
        != "PENDING_APPROVAL"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "action is not pending approval: "
                + str(
                    current.get(
                        "status"
                    )
                )
            ),
        )


    approval_action = SafeAction(
        action=current.get(
            "action",
            "",
        ),
        target=current.get(
            "target",
            "",
        ),
        incident_id=current.get(
            "incident_id",
            "",
        ),
        risk=current.get(
            "risk",
            "UNKNOWN",
        ),
        requires_approval=True,
        rollback=current.get(
            "rollback",
            "",
        ),
        status=current.get(
            "status",
            "PENDING_APPROVAL",
        ),
    )


    policy = _evaluate_operator_policy(
        approval_action
    )


    if (
        policy.get(
            "status"
        )
        != "ALLOWED"
    ):

        try:
            _approval.reject(
                action_id,
                user="ATLAS_POLICY",
            )

        except ValueError as exc:
            raise HTTPException(
                status_code=409,
                detail=str(exc),
            ) from exc


        rejected = (
            _actions.get_action_request(
                action_id
            )
        )

        execution_state = (
            _actions
            .get_action_execution_state(
                action_id
            )
        )


        return {
            "status":
                "BLOCKED",

            "action_request":
                rejected,

            "policy":
                policy,

            "execution": {
                "status":
                    "BLOCKED",

                "approval_id":
                    action_id,

                "result":
                    policy.get(
                        "reason",
                        "operator policy blocked action",
                    ),

                "evidence":
                    [],
            },

            "execution_state":
                execution_state,
        }


    try:
        _approval.approve(
            action_id,
            user=operator_user,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    approved = (
        _actions.get_action_request(
            action_id
        )
    )

    execution = (
        _executor.execute(
            approved
        )
    )

    execution_payload = _execution_dict(execution)

    execution_state = (
        _actions.get_action_execution_state(
            action_id
        )
    )

    verification = (
        execution_payload.get(
            "verification",
            {}
        )
        or {}
    )

    final_status = (
        verification.get(
            "status"
        )
        or execution_payload.get(
            "status",
            "UNKNOWN",
        )
    )

    return {
        "status":
            final_status,

        "action_request":
            _actions.get_action_request(
                action_id
            ),

        "execution":
            execution_payload,

        "execution_state":
            execution_state,

        "policy":
            policy,
    }


@router.post(
    "/actions/{action_id}/reverify"
)
def reverify_action(
    action_id: str,
    operator_user: str = Depends(
        _authenticate_operator
    ),
):

    try:

        verification = (
            _recovery.reverify(
                action_id,
                requested_by=operator_user,
            )
        )

    except LookupError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc


    return {
        "status":
            verification[
                "status"
            ],

        "action_request":
            _actions.get_action_request(
                action_id
            ),

        "verification":
            verification,

        "verification_history":
            _actions
            .get_action_verification_history(
                action_id
            ),

        "execution_state":
            _actions
            .get_action_execution_state(
                action_id
            ),
    }


@router.post(
    "/actions/{action_id}/reject"
)
def reject_action(
    action_id: str,
    operator_user: str = Depends(
        _authenticate_operator
    ),
):

    rejected = (
        _approval.reject(
            action_id,
            user=operator_user,
        )
    )

    return {
        "status": "REJECTED",

        "action_request":
            _actions.get_action_request(
                action_id
            ),

        "approval":
            rejected,
    }
