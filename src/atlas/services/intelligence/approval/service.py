from datetime import datetime, timezone
from uuid import uuid4

from atlas.storage.incident_lifecycle_repository import (
    IncidentLifecycleRepository,
)


class ApprovalService:

    APPROVAL_STATE = "PENDING_APPROVAL"

    APPROVED_STATE = "APPROVED"

    REJECTED_STATE = "REJECTED"

    def __init__(
        self,
        repository=None,
    ):

        self.repository = (
            repository
            or IncidentLifecycleRepository()
        )

    def approve(
        self,
        incident_id: str,
        actor: str = "OPERATOR",
        detail: str = "",
    ):

        return self._transition(
            incident_id=incident_id,
            state=self.APPROVED_STATE,
            actor=actor,
            detail=(
                detail
                or "Action approved by operator"
            ),
        )

    def reject(
        self,
        incident_id: str,
        actor: str = "OPERATOR",
        detail: str = "",
    ):

        return self._transition(
            incident_id=incident_id,
            state=self.REJECTED_STATE,
            actor=actor,
            detail=(
                detail
                or "Action rejected by operator"
            ),
        )

    def _transition(
        self,
        incident_id: str,
        state: str,
        actor: str,
        detail: str,
    ):

        if not incident_id:
            raise ValueError(
                "incident_id is required"
            )

        timeline = self.repository.get_by_incident(
            incident_id
        )

        if not timeline:
            raise ValueError(
                f"Incident not found: {incident_id}"
            )

        current_state = timeline[-1].get(
            "state"
        )

        if current_state != self.APPROVAL_STATE:
            raise ValueError(
                "Invalid approval transition: "
                f"{current_state} -> {state}"
            )

        record = {
            "id": str(uuid4()),
            "incident_id": incident_id,
            "state": state,
            "detail": detail,
            "actor": actor,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        self.repository.save(
            record
        )

        return record


class ActionApprovalService:

    PENDING_STATE = "PENDING_APPROVAL"

    APPROVED_STATE = "APPROVED"

    REJECTED_STATE = "REJECTED"

    def __init__(
        self,
        action_repository,
        lifecycle_repository=None,
    ):

        self.action_repository = action_repository

        self.lifecycle_repository = (
            lifecycle_repository
            or IncidentLifecycleRepository()
        )

    def request(
        self,
        action,
        incident_fingerprint=None,
    ):

        if action is None:
            raise ValueError(
                "action is required"
            )

        incident_id = getattr(
            action,
            "incident_id",
            ""
        )

        action_name = getattr(
            action,
            "action",
            ""
        )

        target = getattr(
            action,
            "target",
            ""
        )

        risk = getattr(
            action,
            "risk",
            "UNKNOWN"
        )

        rollback = getattr(
            action,
            "rollback",
            ""
        )

        status = getattr(
            action,
            "status",
            self.PENDING_STATE
        )

        if not incident_id:
            raise ValueError(
                "action incident_id is required"
            )

        if status != self.PENDING_STATE:
            raise ValueError(
                "action must start in PENDING_APPROVAL"
            )

        record = {
            "id": str(uuid4()),
            "incident_id": incident_id,
            "action": action_name,
            "target": target,
            "risk": risk,
            "rollback": rollback,
            "status": self.PENDING_STATE,
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "approved_by": None,
            "approved_at": None,
            "incident_fingerprint": (
                incident_fingerprint
                or getattr(
                    action,
                    "incident_fingerprint",
                    None,
                )
            ),
        }

        self.action_repository.save_action_request(
            record
        )

        self._save_lifecycle_event(
            incident_id=incident_id,
            state=self.PENDING_STATE,
            detail="Action requires operator approval",
            actor="ATLAS",
        )

        return record

    def approve(
        self,
        action_id,
        user="OPERATOR",
    ):

        return self._resolve(
            action_id=action_id,
            status=self.APPROVED_STATE,
            user=user,
            detail="Action approved by operator",
        )

    def reject(
        self,
        action_id,
        user="OPERATOR",
    ):

        return self._resolve(
            action_id=action_id,
            status=self.REJECTED_STATE,
            user=user,
            detail="Action rejected by operator",
        )

    def _resolve(
        self,
        action_id,
        status,
        user,
        detail,
    ):

        if not action_id:
            raise ValueError(
                "action_id is required"
            )

        action = (
            self.action_repository
            .get_action_request(
                action_id
            )
        )

        if not action:
            raise ValueError(
                f"Action request not found: {action_id}"
            )

        current_status = action.get(
            "status"
        )

        if current_status != self.PENDING_STATE:
            raise ValueError(
                "Invalid approval transition: "
                f"{current_status} -> {status}"
            )

        self.action_repository.update_action_status(
            action_id,
            status,
            user,
        )

        self._save_lifecycle_event(
            incident_id=action.get(
                "incident_id",
                ""
            ),
            state=status,
            detail=detail,
            actor=user,
        )

        updated = (
            self.action_repository
            .get_action_request(
                action_id
            )
        )

        return updated

    def _save_lifecycle_event(
        self,
        incident_id,
        state,
        detail,
        actor,
    ):

        if not incident_id:
            raise ValueError(
                "incident_id is required for lifecycle event"
            )

        event = {
            "id": str(uuid4()),
            "incident_id": incident_id,
            "state": state,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "detail": detail,
            "actor": actor,
        }

        self.lifecycle_repository.save(
            event
        )

        return event
