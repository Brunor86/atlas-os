from datetime import datetime, timezone
import uuid

from atlas.models.execution import ActionExecution
from atlas.services.intelligence.execution.validators import ActionValidator
from atlas.services.intelligence.execution.handlers.docker import DockerActionHandler
from atlas.services.intelligence.execution.handlers.systemd import SystemdActionHandler
from atlas.services.intelligence.execution.handlers.proxmox import ProxmoxActionHandler
from atlas.services.intelligence.learning.service import IncidentLearningService


class ActionExecutionService:


    #
    # Single source of truth for concrete execution capability.
    #
    # ActionValidator answers whether an action belongs to ATLAS
    # policy vocabulary.
    #
    # This table answers whether ATLAS currently has a concrete
    # execution route for that action.
    #
    _EXECUTION_ROUTES = {

        "start container":
            (
                "docker",
                "start_container",
            ),

        "restart container":
            (
                "docker",
                "restart_container",
            ),

        "stop container":
            (
                "docker",
                "stop_container",
            ),

        "start service":
            (
                "systemd",
                "start_service",
            ),

        "restart service":
            (
                "systemd",
                "restart_service",
            ),

        "stop service":
            (
                "systemd",
                "stop_service",
            ),

        "start vm":
            (
                "proxmox",
                "start_vm",
            ),

        "stop vm":
            (
                "proxmox",
                "stop_vm",
            ),

        "restart vm":
            (
                "proxmox",
                "restart_vm",
            ),

        "start lxc":
            (
                "proxmox",
                "start_lxc",
            ),

        "restart lxc":
            (
                "proxmox",
                "restart_lxc",
            ),

        "stop lxc":
            (
                "proxmox",
                "stop_lxc",
            ),

    }


    @classmethod
    def _resolve_execution_route(
        cls,
        action,
    ):

        normalized = str(
            action
            or ""
        ).strip()

        route = (
            cls._EXECUTION_ROUTES.get(
                normalized
            )
        )

        if route is None:
            return None


        backend, method_name = route

        handler_types = {

            "docker":
                DockerActionHandler,

            "systemd":
                SystemdActionHandler,

            "proxmox":
                ProxmoxActionHandler,

        }

        handler_type = (
            handler_types.get(
                backend
            )
        )

        if handler_type is None:
            return None


        method = getattr(
            handler_type,
            method_name,
            None,
        )

        if not callable(
            method
        ):
            return None


        return route


    @classmethod
    def is_action_executable(
        cls,
        action,
    ) -> bool:

        return (
            cls._resolve_execution_route(
                action
            )
            is not None
        )


    def _execute_route(
        self,
        route,
        target,
    ):

        backend, method_name = route


        if backend == "docker":

            handler = self.docker


        elif backend == "systemd":

            handler = self.systemd


        elif backend == "proxmox":

            handler = (
                ProxmoxActionHandler()
            )


        else:

            return {
                "status":
                    "REJECTED",

                "result":
                    "no execution handler for route",

                "evidence": [
                    "execution route backend unavailable",
                ],
            }


        method = getattr(
            handler,
            method_name,
            None,
        )

        if not callable(
            method
        ):

            return {
                "status":
                    "REJECTED",

                "result":
                    "no execution handler for route",

                "evidence": [
                    "execution route method unavailable",
                ],
            }


        return method(
            target
        )


    def __init__(
        self,
        repository=None,
        learning_repository=None,
    ):

        self.repository = repository

        self.learning_repository = learning_repository or repository

        self.validator = ActionValidator()

        self.docker = DockerActionHandler()

        self.systemd = SystemdActionHandler()

        self.learning = IncidentLearningService(
            self.learning_repository
        )



    def execute(
        self,
        approval,
    ):

        if not approval:
            raise ValueError("approval is required")

        if approval.get("status") != "APPROVED":
            execution = ActionExecution(
                approval_id=approval.get("id", ""),
                incident_id=approval.get(
                    "incident_id",
                    "",
                ),
                action=approval.get(
                    "action",
                    "",
                ),
                target=approval.get(
                    "target",
                    "",
                ),
                status="REJECTED",
                result="action is not approved",
                executed_at=datetime.now(timezone.utc).isoformat(),
            )

            return execution

        validation = self.validator.validate(
            approval.get("action")
        )


        if not validation["valid"]:

            execution = ActionExecution(

                approval_id=approval["id"],

                incident_id=approval.get(
                    "incident_id",
                    ""
                ),

                action=approval.get(
                    "action",
                    ""
                ),

                target=approval.get(
                    "target",
                    ""
                ),

                status="REJECTED",

                result=validation["reason"],

                executed_at=datetime.now(timezone.utc).isoformat(),

            )

            return execution



        action_result = {

            "status": "REJECTED",

            "result": (
                "no execution handler for action: "
                + str(
                    approval.get(
                        "action",
                        "",
                    )
                )
            ),

            "evidence": [
                "no explicit execution route",
            ],

        }


        route = (
            self._resolve_execution_route(
                approval.get(
                    "action"
                )
            )
        )


        if route is not None:

            action_result = (
                self._execute_route(
                    route,
                    approval.get(
                        "target"
                    ),
                )
            )


        execution = ActionExecution(

            approval_id=approval["id"],

            incident_id=approval.get(
                "incident_id",
                ""
            ),

            action=approval["action"],

            target=approval["target"],

            status=action_result["status"],

            result=action_result["result"],

            executed_at=datetime.now(timezone.utc).isoformat(),

            evidence=action_result.get(
                "evidence",
                []
            ),

        )


        if self.repository:

            self.repository.save_action_history(
                {
                    "id": str(uuid.uuid4()),

                    "approval_id": execution.approval_id,

                    "action": execution.action,

                    "target": execution.target,

                    "status": execution.status,

                    "result": execution.result,

                    "executed_at": execution.executed_at,

                    "evidence": execution.evidence,

                }
            )


        if execution.status == "SUCCESS":

            if (
                self.repository
                and hasattr(
                    self.repository,
                    "mark_action_executed",
                )
            ):

                self.repository.mark_action_executed(
                    execution.approval_id
                )


            #
            # Production ActionRepository supports a distinct,
            # persisted post-execution verification phase.
            #
            # Legacy/test repositories without that capability
            # preserve the historical behavior.
            #
            verification_managed = (
                self.repository
                and hasattr(
                    self.repository,
                    "finalize_action_verification",
                )
            )


            if not verification_managed:

                self.learning.learn(

                    incident_id=execution.incident_id,

                    action=execution.action,

                    result=execution.status,

                    resolution=execution.result,

                    evidence=execution.evidence,

                )



        return execution
