from __future__ import annotations

import re
import subprocess
from types import SimpleNamespace
from typing import Annotated, Any, Literal
from uuid import uuid4

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from atlas.models.action import SafeAction
from atlas.services.proxmox import ProxmoxService
from atlas.services.intelligence.approval.service import (
    ActionApprovalService,
)
from atlas.services.intelligence.safety.service import (
    ActionSafetyService,
)
from atlas.storage.action_repository import (
    ActionRepository,
)
from atlas.storage.database import Database


class AtlasOperatorResult(BaseModel):

    status: str

    data: dict[str, Any]


#
# This MCP is intentionally NOT read-only.
#
# However, its first capability only creates an action proposal.
# It does not approve or execute infrastructure changes.
#
PROPOSAL_TOOL = ToolAnnotations(
    read_only_hint=False,
    idempotent_hint=False,
    open_world_hint=False,
)


_TARGET_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$"
)


_SERVICE_RE = re.compile(
    r"^[A-Za-z0-9]"
    r"[A-Za-z0-9_.@:-]{0,127}"
    r"\.service$"
)


_PROXMOX_VMID_RE = re.compile(
    r"^[1-9][0-9]{0,8}$"
)


PROTECTED_SERVICES = {
    "atlas-web.service",
    "docker.service",
    "containerd.service",
    "ssh.service",
    "systemd-journald.service",
    "systemd-logind.service",
    "systemd-udevd.service",
}


class _NoopLifecycleRepository:

    def save(
        self,
        event,
    ):
        return event


class OperatorProposalService:
    """
    Build persistent SafeAction proposals.

    This service may create an action request in ATLAS persistence,
    but it must never execute infrastructure changes.
    """

    def __init__(
        self,
        action_repository=None,
        safety=None,
        proxmox=None,
    ):

        if action_repository is None:

            database = Database()

            action_repository = (
                ActionRepository(
                    database
                )
            )

        self.actions = (
            action_repository
        )

        self.safety = (
            safety
            or ActionSafetyService()
        )

        self.proxmox = proxmox

        self.approval = (
            ActionApprovalService(
                action_repository=(
                    self.actions
                ),
                lifecycle_repository=(
                    _NoopLifecycleRepository()
                ),
            )
        )


    def _proxmox_guest_state(
        self,
        resource_type: str,
        target: str,
    ) -> dict[str, Any]:

        resource_type = str(
            resource_type or ""
        ).strip().lower()

        target = str(
            target or ""
        ).strip()

        if resource_type not in (
            "vm",
            "lxc",
        ):

            return {
                "status":
                    "BLOCKED",

                "reason":
                    "unsupported Proxmox guest resource type",
            }

        if not _PROXMOX_VMID_RE.fullmatch(
            target
        ):

            return {
                "status":
                    "BLOCKED",

                "reason":
                    "invalid Proxmox VMID",
            }

        expected_type = {
            "vm":
                "qemu",

            "lxc":
                "lxc",
        }[
            resource_type
        ]

        try:

            proxmox = (
                self.proxmox
                or ProxmoxService()
            )

            guest = proxmox.resolve_guest(
                int(
                    target
                ),
                expected_type=expected_type,
            )

        except LookupError as exc:

            return {
                "status":
                    "NOT_FOUND",

                "reason":
                    str(
                        exc
                    ),
            }

        except ValueError as exc:

            return {
                "status":
                    "BLOCKED",

                "reason":
                    str(
                        exc
                    ),
            }

        except Exception as exc:

            return {
                "status":
                    "ERROR",

                "reason":
                    str(
                        exc
                    ),
            }

        guest_status = str(
            guest.status
            or "unknown"
        ).strip().lower()

        if guest_status not in (
            "running",
            "stopped",
        ):

            return {
                "status":
                    "BLOCKED",

                "reason": (
                    "unsupported Proxmox guest status: "
                    + guest_status
                ),

                "target":
                    str(
                        guest.vmid
                    ),

                "guest_status":
                    guest_status,
            }

        return {
            "status":
                "SUCCESS",

            "resource_type":
                resource_type,

            "target":
                str(
                    guest.vmid
                ),

            "vmid":
                guest.vmid,

            "name":
                guest.name,

            "node":
                guest.node,

            "proxmox_type":
                guest.type,

            "guest_status":
                guest_status,

            "running":
                guest_status
                == "running",
        }


    def propose_proxmox_guest_action(
        self,
        resource_type: str,
        action: str,
        target: str,
    ) -> dict[str, Any]:

        resource_type = str(
            resource_type or ""
        ).strip().lower()

        action = str(
            action or ""
        ).strip().lower()

        target = str(
            target or ""
        ).strip()

        if resource_type not in (
            "vm",
            "lxc",
        ):

            return {
                "status":
                    "BLOCKED",

                "reason":
                    "unsupported Proxmox guest resource type",
            }

        action_map = {
            "start":
                f"start {resource_type}",

            "restart":
                f"restart {resource_type}",

            "stop":
                f"stop {resource_type}",
        }

        action_name = (
            action_map.get(
                action
            )
        )

        if not action_name:

            return {
                "status":
                    "BLOCKED",

                "reason":
                    "unsupported Proxmox guest action",
            }

        state = (
            self._proxmox_guest_state(
                resource_type,
                target,
            )
        )

        if (
            state.get(
                "status"
            )
            != "SUCCESS"
        ):

            return state

        running = bool(
            state.get(
                "running"
            )
        )

        if (
            action == "start"
            and running
        ):

            return {
                "status":
                    "BLOCKED",

                "reason":
                    "Proxmox guest is already running",

                "resource_type":
                    resource_type,

                "target":
                    target,

                "target_state":
                    "RUNNING",
            }

        if (
            action == "restart"
            and not running
        ):

            return {
                "status":
                    "BLOCKED",

                "reason": (
                    "Proxmox guest is stopped; "
                    "use action='start'"
                ),

                "resource_type":
                    resource_type,

                "target":
                    target,

                "target_state":
                    "STOPPED",
            }

        if (
            action == "stop"
            and not running
        ):

            return {
                "status":
                    "BLOCKED",

                "reason":
                    "Proxmox guest is already stopped",

                "resource_type":
                    resource_type,

                "target":
                    target,

                "target_state":
                    "STOPPED",
            }

        operation_id = (
            "OP-"
            + str(
                uuid4()
            )
        )

        safety_incident = (
            SimpleNamespace(
                incident_id=operation_id,
                asset=target,
                diagnosis={},
                recommendation={
                    "action":
                        action_name,

                    "incident_id":
                        operation_id,

                    "evidence": [
                        {
                            "source":
                                "atlas-operator-mcp",

                            "type":
                                "operator-proxmox-guest-proposal",

                            "resource_type":
                                resource_type,

                            "target":
                                target,

                            "vmid":
                                state.get(
                                    "vmid"
                                ),

                            "name":
                                state.get(
                                    "name"
                                ),

                            "node":
                                state.get(
                                    "node"
                                ),

                            "proxmox_type":
                                state.get(
                                    "proxmox_type"
                                ),

                            "guest_status":
                                state.get(
                                    "guest_status"
                                ),

                            "requested_action":
                                action,
                        }
                    ],
                },
            )
        )

        safety = (
            self.safety.evaluate(
                safety_incident
            )
        )

        if (
            safety.get(
                "status"
            )
            == "BLOCKED"
        ):

            return {
                "status":
                    "BLOCKED",

                "reason":
                    safety.get(
                        "reason",
                        "safety policy rejected action",
                    ),

                "safety":
                    safety,
            }

        safe_action = SafeAction(
            action=safety.get(
                "action",
                action_name,
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
            requires_approval=True,
            rollback=safety.get(
                "rollback",
                "",
            ),
            status="PENDING_APPROVAL",
            evidence=safety.get(
                "evidence",
                [],
            ),
        )

        request = (
            self.approval.request(
                safe_action
            )
        )

        return {
            "status":
                "PENDING_APPROVAL",

            "resource_type":
                resource_type,

            "action_request":
                request,

            "guest": {
                "vmid":
                    state.get(
                        "vmid"
                    ),

                "name":
                    state.get(
                        "name"
                    ),

                "node":
                    state.get(
                        "node"
                    ),

                "proxmox_type":
                    state.get(
                        "proxmox_type"
                    ),

                "status":
                    state.get(
                        "guest_status"
                    ),
            },

            "target_state": (
                "RUNNING"
                if running
                else "STOPPED"
            ),

            "safety": {
                "validated":
                    True,

                "risk":
                    safe_action.risk,
            },

            "requires_approval":
                True,

            "execution_allowed":
                False,
        }


    def _container_state(
        self,
        target: str,
    ) -> dict[str, Any]:

        if not _TARGET_RE.fullmatch(
            target
        ):
            return {
                "status": "BLOCKED",
                "reason": (
                    "invalid container target"
                ),
            }

        try:

            inspect = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "--type",
                    "container",
                    "-f",
                    (
                        "{{.Name}}|"
                        "{{.State.Running}}"
                    ),
                    target,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

        except Exception as exc:

            return {
                "status": "ERROR",
                "reason": str(exc),
            }


        if inspect.returncode != 0:

            return {
                "status": "NOT_FOUND",
                "reason": (
                    "Docker container not found: "
                    + target
                ),
            }


        raw = (
            inspect.stdout
            .strip()
        )

        try:
            name, running_raw = (
                raw.split(
                    "|",
                    1,
                )
            )
        except ValueError:

            return {
                "status": "ERROR",
                "reason": (
                    "invalid Docker inspection result"
                ),
            }


        canonical = (
            name.lstrip("/")
        )

        if canonical != target:

            return {
                "status": "BLOCKED",
                "reason": (
                    "target must be the canonical "
                    "container name"
                ),
            }


        return {
            "status": "SUCCESS",
            "target": canonical,
            "running": (
                running_raw
                .strip()
                .lower()
                == "true"
            ),
        }


    def _service_state(
        self,
        target: str,
    ) -> dict[str, Any]:

        if not _SERVICE_RE.fullmatch(
            target
        ):
            return {
                "status": "BLOCKED",
                "reason": (
                    "invalid systemd service target"
                ),
            }

        if target in PROTECTED_SERVICES:
            return {
                "status": "BLOCKED",
                "reason": (
                    "protected systemd service: "
                    + target
                ),
                "target": target,
            }

        try:

            show = subprocess.run(
                [
                    "systemctl",
                    "show",
                    target,
                    "--property=Id",
                    "--property=LoadState",
                    "--value",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

        except Exception as exc:

            return {
                "status": "ERROR",
                "reason": str(exc),
            }

        if show.returncode != 0:

            return {
                "status": "NOT_FOUND",
                "reason": (
                    "systemd service not found: "
                    + target
                ),
            }

        lines = [
            line.strip()
            for line in show.stdout.splitlines()
            if line.strip()
        ]

        if len(lines) < 2:

            return {
                "status": "ERROR",
                "reason": (
                    "invalid systemd inspection result"
                ),
            }

        canonical = lines[0]
        load_state = lines[1]

        if canonical != target:

            return {
                "status": "BLOCKED",
                "reason": (
                    "target must be the canonical "
                    "systemd service name"
                ),
            }

        if load_state != "loaded":

            return {
                "status": "NOT_FOUND",
                "reason": (
                    "systemd service is not loaded: "
                    + target
                ),
            }

        active = subprocess.run(
            [
                "systemctl",
                "is-active",
                target,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        active_state = (
            active.stdout
            .strip()
            .lower()
        )

        running = (
            active_state
            == "active"
        )

        return {
            "status": "SUCCESS",
            "target": canonical,
            "running": running,
            "active_state": active_state,
        }


    def propose_service_action(
        self,
        action: str,
        target: str,
    ) -> dict[str, Any]:

        action = str(
            action or ""
        ).strip().lower()

        target = str(
            target or ""
        ).strip()


        action_map = {
            "start":
                "start service",

            "restart":
                "restart service",

            "stop":
                "stop service",
        }


        action_name = (
            action_map.get(
                action
            )
        )

        if not action_name:

            return {
                "status": "BLOCKED",
                "reason": (
                    "unsupported service action"
                ),
            }


        state = (
            self._service_state(
                target
            )
        )

        if (
            state.get(
                "status"
            )
            != "SUCCESS"
        ):
            return state


        running = bool(
            state.get(
                "running"
            )
        )


        if (
            action == "start"
            and running
        ):

            return {
                "status": "BLOCKED",
                "reason": (
                    "service is already active"
                ),
                "target": target,
                "target_state": "RUNNING",
            }


        if (
            action == "restart"
            and not running
        ):

            return {
                "status": "BLOCKED",
                "reason": (
                    "service is inactive; "
                    "use action='start'"
                ),
                "target": target,
                "target_state": "STOPPED",
            }


        if (
            action == "stop"
            and not running
        ):

            return {
                "status": "BLOCKED",
                "reason": (
                    "service is already inactive"
                ),
                "target": target,
                "target_state": "STOPPED",
            }


        operation_id = (
            "OP-"
            + str(uuid4())
        )


        safety_incident = (
            SimpleNamespace(
                incident_id=operation_id,
                asset=target,
                diagnosis={},
                recommendation={
                    "action":
                        action_name,

                    "incident_id":
                        operation_id,

                    "evidence": [
                        {
                            "source":
                                "atlas-operator-mcp",

                            "type":
                                "operator-service-proposal",

                            "target":
                                target,

                            "requested_action":
                                action,

                            "active_state":
                                state.get(
                                    "active_state"
                                ),
                        }
                    ],
                },
            )
        )


        safety = (
            self.safety.evaluate(
                safety_incident
            )
        )


        if (
            safety.get(
                "status"
            )
            == "BLOCKED"
        ):

            return {
                "status": "BLOCKED",
                "reason": safety.get(
                    "reason",
                    "safety policy rejected action",
                ),
                "safety": safety,
            }


        safe_action = SafeAction(
            action=safety.get(
                "action",
                action_name,
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
            requires_approval=True,
            rollback=safety.get(
                "rollback",
                "",
            ),
            status="PENDING_APPROVAL",
            evidence=safety.get(
                "evidence",
                [],
            ),
        )


        request = (
            self.approval.request(
                safe_action
            )
        )


        return {
            "status":
                "PENDING_APPROVAL",

            "resource_type":
                "service",

            "action_request":
                request,

            "target_state": (
                "RUNNING"
                if running
                else "STOPPED"
            ),

            "safety": {
                "validated":
                    True,

                "risk":
                    safe_action.risk,
            },

            "requires_approval":
                True,

            "execution_allowed":
                False,
        }


    def propose_container_action(
        self,
        action: str,
        target: str,
    ) -> dict[str, Any]:

        action = str(
            action or ""
        ).strip().lower()

        target = str(
            target or ""
        ).strip()


        action_map = {
            "start":
                "start container",

            "restart":
                "restart container",

            "stop":
                "stop container",
        }


        action_name = (
            action_map.get(
                action
            )
        )

        if not action_name:

            return {
                "status": "BLOCKED",
                "reason": (
                    "unsupported container action"
                ),
            }


        state = (
            self._container_state(
                target
            )
        )

        if (
            state.get(
                "status"
            )
            != "SUCCESS"
        ):
            return state


        running = bool(
            state.get(
                "running"
            )
        )


        if (
            action == "start"
            and running
        ):

            return {
                "status": "BLOCKED",
                "reason": (
                    "container is already running"
                ),
                "target": target,
                "target_state": "RUNNING",
            }


        if (
            action == "restart"
            and not running
        ):

            return {
                "status": "BLOCKED",
                "reason": (
                    "container is stopped; "
                    "use action='start'"
                ),
                "target": target,
                "target_state": "STOPPED",
            }


        if (
            action == "stop"
            and not running
        ):

            return {
                "status": "BLOCKED",
                "reason": (
                    "container is already stopped"
                ),
                "target": target,
                "target_state": "STOPPED",
            }


        operation_id = (
            "OP-"
            + str(uuid4())
        )


        safety_incident = (
            SimpleNamespace(
                incident_id=operation_id,
                asset=target,
                diagnosis={},
                recommendation={
                    "action":
                        action_name,

                    "incident_id":
                        operation_id,

                    "evidence": [
                        {
                            "source":
                                "atlas-operator-mcp",

                            "type":
                                "operator-proposal",

                            "target":
                                target,

                            "requested_action":
                                action,
                        }
                    ],
                },
            )
        )


        safety = (
            self.safety.evaluate(
                safety_incident
            )
        )


        if (
            safety.get(
                "status"
            )
            == "BLOCKED"
        ):

            return {
                "status": "BLOCKED",
                "reason": safety.get(
                    "reason",
                    "safety policy rejected action",
                ),
                "safety": safety,
            }


        safe_action = SafeAction(
            action=safety.get(
                "action",
                action_name,
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
            requires_approval=True,
            rollback=safety.get(
                "rollback",
                "",
            ),
            status="PENDING_APPROVAL",
            evidence=safety.get(
                "evidence",
                [],
            ),
        )


        request = (
            self.approval.request(
                safe_action
            )
        )


        return {
            "status":
                "PENDING_APPROVAL",

            "action_request":
                request,

            "target_state": (
                "RUNNING"
                if running
                else "STOPPED"
            ),

            "safety": {
                "validated":
                    True,

                "risk":
                    safe_action.risk,
            },

            "requires_approval":
                True,

            "execution_allowed":
                False,
        }


def _wrap(
    result: dict[str, Any],
) -> AtlasOperatorResult:

    return AtlasOperatorResult(
        status=str(
            result.get(
                "status",
                "ERROR",
            )
        ),
        data=result,
    )


def build_operator_server(
    proposal_service=None,
) -> MCPServer:

    proposer = (
        proposal_service
        or OperatorProposalService()
    )


    server = MCPServer(
        "atlas-operator",
        instructions=(
            "Controlled operational proposal interface for ATLAS. "
            "Tools may propose typed infrastructure actions but must "
            "never bypass ATLAS safety, approval or execution policy. "
            "A PENDING_APPROVAL result means no infrastructure change "
            "has been executed."
        ),
    )


    @server.tool(
        name="atlas_propose_container_action",
        title="Propose a controlled Docker container action",
        description=(
            "Create a persistent ATLAS SafeAction proposal for a Docker "
            "container. Supported actions are start, restart and stop. "
            "This tool never approves or executes the action. "
            "A successful result is PENDING_APPROVAL and requires a "
            "separate human approval before ATLAS may execute anything."
        ),
        annotations=PROPOSAL_TOOL,
    )
    def atlas_propose_container_action(
        action: Literal[
            "start",
            "restart",
            "stop",
        ],
        target: Annotated[
            str,
            Field(
                min_length=1,
                max_length=128,
                pattern=(
                    r"^[A-Za-z0-9]"
                    r"[A-Za-z0-9_.-]{0,127}$"
                ),
            ),
        ],
    ) -> AtlasOperatorResult:

        return _wrap(
            proposer
            .propose_container_action(
                action=action,
                target=target,
            )
        )


    @server.tool(
        name="atlas_propose_service_action",
        title="Propose a controlled systemd service action",
        description=(
            "Create a persistent ATLAS SafeAction proposal for a "
            "systemd service. Supported actions are start, restart "
            "and stop. This tool never approves or executes the action. "
            "A successful result is PENDING_APPROVAL and requires a "
            "separate human approval before ATLAS may execute anything."
        ),
        annotations=PROPOSAL_TOOL,
    )
    def atlas_propose_service_action(
        action: Literal[
            "start",
            "restart",
            "stop",
        ],
        target: Annotated[
            str,
            Field(
                min_length=9,
                max_length=136,
                pattern=(
                    r"^[A-Za-z0-9]"
                    r"[A-Za-z0-9_.@:-]{0,127}"
                    r"\.service$"
                ),
            ),
        ],
    ) -> AtlasOperatorResult:

        return _wrap(
            proposer
            .propose_service_action(
                action=action,
                target=target,
            )
        )


    @server.tool(
        name="atlas_propose_proxmox_guest_action",
        title="Propose a controlled Proxmox guest action",
        description=(
            "Create a persistent ATLAS SafeAction proposal for a "
            "Proxmox QEMU VM or LXC guest identified by numeric VMID. "
            "Supported actions are start, restart and stop. "
            "ATLAS verifies the VMID, concrete guest type, node and "
            "current state using the Proxmox API. "
            "This tool never approves or executes the action. "
            "A successful result is PENDING_APPROVAL."
        ),
        annotations=PROPOSAL_TOOL,
    )
    def atlas_propose_proxmox_guest_action(
        resource_type: Literal[
            "vm",
            "lxc",
        ],
        action: Literal[
            "start",
            "restart",
            "stop",
        ],
        target: Annotated[
            str,
            Field(
                min_length=1,
                max_length=9,
                pattern=(
                    r"^[1-9][0-9]{0,8}$"
                ),
            ),
        ],
    ) -> AtlasOperatorResult:

        return _wrap(
            proposer
            .propose_proxmox_guest_action(
                resource_type=resource_type,
                action=action,
                target=target,
            )
        )


    return server


mcp = build_operator_server()


if __name__ == "__main__":
    mcp.run()
