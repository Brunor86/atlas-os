from __future__ import annotations

import ast
import hashlib
import json

from atlas.models.action import SafeAction
from atlas.services.intelligence.approval.service import (
    ActionApprovalService,
)
from atlas.services.intelligence.operator import (
    IntelligenceOperator,
)
from atlas.storage.action_repository import (
    ActionRepository,
)
from atlas.storage.database import Database
from atlas.storage.incident_repository import (
    IncidentRepository,
)


class IncidentActionProposalService:
    """
    Bridge incident intelligence into the persistent
    human-approval workflow.

    This service may create a PENDING_APPROVAL request.
    It never approves or executes infrastructure actions.

    Proposal identity is decision-aware:
    the same action/target for the same material incident
    state must not be repeatedly proposed.
    """

    DECISION_STATES = {
        "REJECTED",
        "APPROVED",
        "AUTO_APPROVED",
        "EXECUTED",
    }


    def __init__(
        self,
        operator=None,
        action_repository=None,
        approval=None,
        incident_repository=None,
        registry=None,
    ):

        if action_repository is None:

            action_repository = ActionRepository(
                Database()
            )

        self.actions = action_repository

        if operator is None:

            incident_repository = (
                incident_repository
                or IncidentRepository()
            )

            operator = IntelligenceOperator(
                repository=incident_repository,
                registry=registry,
            )

        self.operator = operator

        self.approval = (
            approval
            or ActionApprovalService(
                action_repository=self.actions
            )
        )


    @classmethod
    def _normalize_fingerprint_value(
        cls,
        value,
    ):

        if isinstance(
            value,
            str,
        ):

            text = value.strip()

            if not text:
                return ""

            try:
                parsed = ast.literal_eval(
                    text
                )
            except Exception:
                return text

            if parsed == value:
                return text

            return (
                cls._normalize_fingerprint_value(
                    parsed
                )
            )

        if isinstance(
            value,
            dict,
        ):

            return {
                str(key):
                    cls._normalize_fingerprint_value(
                        item
                    )
                for key, item
                in sorted(
                    value.items(),
                    key=lambda pair:
                        str(pair[0]),
                )
            }

        if isinstance(
            value,
            (list, tuple, set),
        ):

            normalized = [
                cls._normalize_fingerprint_value(
                    item
                )
                for item in value
            ]

            return sorted(
                normalized,
                key=lambda item:
                    json.dumps(
                        item,
                        sort_keys=True,
                        default=str,
                    ),
            )

        return value


    @classmethod
    def _incident_fingerprint(
        cls,
        incident,
    ):

        record = (
            IncidentRepository._record(
                incident
            )
        )

        if record is None:
            raise ValueError(
                "incident is required for fingerprint"
            )

        #
        # Deliberately exclude created_at / updated_at.
        #
        # IncidentManager refreshes updated_at during normal
        # NOC synchronization even when the material incident
        # state did not change.
        #
        keys = (
            "id",
            "title",
            "asset_id",
            "severity",
            "status",
            "evidence",
            "recommendations",
            "impact",
            "impact_intelligence",
            "root_cause",
            "diagnosis",
            "blast_radius",
            "suggested_actions",
        )

        payload = {
            key:
                cls._normalize_fingerprint_value(
                    record.get(
                        key
                    )
                )
            for key in keys
        }

        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
            default=str,
        )

        return hashlib.sha256(
            encoded.encode(
                "utf-8"
            )
        ).hexdigest()


    @staticmethod
    def _normalize_request(
        record,
    ):

        if record is None:
            return None

        if isinstance(
            record,
            dict,
        ):
            return dict(
                record
            )

        if isinstance(
            record,
            (tuple, list),
        ) and len(record) >= 10:

            normalized = {
                "id":
                    record[0],

                "incident_id":
                    record[1],

                "action":
                    record[2],

                "target":
                    record[3],

                "risk":
                    record[4],

                "rollback":
                    record[5],

                "status":
                    record[6],

                "created_at":
                    record[7],

                "approved_by":
                    record[8],

                "approved_at":
                    record[9],
            }

            if len(record) > 10:
                normalized[
                    "incident_fingerprint"
                ] = record[10]

            return normalized

        return None


    def _matching_requests(
        self,
        incident_id,
        action,
        target,
    ):

        getter = getattr(
            self.actions,
            "get_action_requests_by_incident",
            None,
        )

        if callable(
            getter
        ):
            raw_records = getter(
                incident_id
            )
        else:
            raw_records = (
                self.actions
                .get_pending_actions()
            )

        result = []

        for raw in raw_records:

            record = (
                self._normalize_request(
                    raw
                )
            )

            if not record:
                continue

            if (
                str(
                    record.get(
                        "incident_id"
                    )
                    or ""
                )
                != incident_id
            ):
                continue

            if (
                str(
                    record.get(
                        "action"
                    )
                    or ""
                )
                != action
            ):
                continue

            if (
                str(
                    record.get(
                        "target"
                    )
                    or ""
                )
                != target
            ):
                continue

            result.append(
                record
            )

        return result


    def _backfill_fingerprint(
        self,
        record,
        fingerprint,
    ):

        if record.get(
            "incident_fingerprint"
        ):
            return record

        updater = getattr(
            self.actions,
            "update_action_fingerprint",
            None,
        )

        action_id = record.get(
            "id"
        )

        if (
            callable(
                updater
            )
            and action_id
        ):
            updater(
                action_id,
                fingerprint,
            )

        record[
            "incident_fingerprint"
        ] = fingerprint

        return record


    def propose(
        self,
        incident_id,
    ):

        incident_id = str(
            incident_id
            or ""
        ).strip()

        if not incident_id:

            raise ValueError(
                "incident_id is required"
            )


        analysis = (
            self.operator.analyze(
                incident_id
            )
        )

        incident = analysis.get(
            "incident"
        )

        fingerprint = (
            self._incident_fingerprint(
                incident
            )
        )

        safety = (
            analysis.get(
                "safety"
            )
            or {}
        )

        if not isinstance(
            safety,
            dict,
        ):

            return {
                "status":
                    "NO_PROPOSAL",

                "incident_id":
                    incident_id,

                "reason":
                    "invalid safety result",
            }


        safety_status = str(
            safety.get(
                "status"
            )
            or ""
        ).strip().upper()


        if safety_status in (
            "NO_ACTION",
            "BLOCKED",
        ):

            return {
                "status":
                    safety_status,

                "incident_id":
                    incident_id,

                "reason":
                    safety.get(
                        "reason",
                        "",
                    ),

                "safety":
                    safety,
            }


        action = str(
            safety.get(
                "action"
            )
            or ""
        ).strip()

        target = str(
            safety.get(
                "target"
            )
            or ""
        ).strip()

        action_incident_id = str(
            safety.get(
                "incident_id"
            )
            or incident_id
        ).strip()


        if not action or not target:

            return {
                "status":
                    "NO_PROPOSAL",

                "incident_id":
                    incident_id,

                "reason":
                    (
                        "safety result has no "
                        "actionable action and target"
                    ),

                "safety":
                    safety,
            }


        requires_approval = bool(
            safety.get(
                "requires_approval",
                False,
            )
        )

        if (
            safety_status
            != "PENDING_APPROVAL"
            or not requires_approval
        ):

            return {
                "status":
                    "NO_PROPOSAL",

                "incident_id":
                    incident_id,

                "reason":
                    (
                        "safety result does not require "
                        "human approval"
                    ),

                "safety":
                    safety,
            }


        previous = (
            self._matching_requests(
                action_incident_id,
                action,
                target,
            )
        )


        #
        # A pending request always wins over creation of
        # another pending request.
        #
        for record in previous:

            status = str(
                record.get(
                    "status"
                )
                or ""
            ).upper()

            if status != "PENDING_APPROVAL":
                continue

            existing_fingerprint = (
                record.get(
                    "incident_fingerprint"
                )
            )

            if not existing_fingerprint:

                record = (
                    self._backfill_fingerprint(
                        record,
                        fingerprint,
                    )
                )

                existing_fingerprint = (
                    fingerprint
                )

            if (
                existing_fingerprint
                == fingerprint
            ):

                return {
                    "status":
                        "PENDING_APPROVAL",

                    "incident_id":
                        action_incident_id,

                    "action_request":
                        record,

                    "created":
                        False,

                    "idempotent":
                        True,

                    "incident_fingerprint":
                        fingerprint,

                    "safety":
                        safety,
                }

            #
            # The incident changed while the operator still
            # has an old decision pending. Do not create a
            # second approval against a newer state.
            #
            return {
                "status":
                    "STALE_PENDING",

                "incident_id":
                    action_incident_id,

                "action_request":
                    record,

                "created":
                    False,

                "idempotent":
                    True,

                "incident_fingerprint":
                    fingerprint,

                "reason":
                    (
                        "incident changed while an older "
                        "action request is still pending"
                    ),

                "safety":
                    safety,
            }


        #
        # Respect a human decision / successful execution
        # for the same material incident state.
        #
        for record in previous:

            status = str(
                record.get(
                    "status"
                )
                or ""
            ).upper()

            if (
                status
                not in self.DECISION_STATES
            ):
                continue

            existing_fingerprint = (
                record.get(
                    "incident_fingerprint"
                )
            )

            #
            # Legacy terminal requests have no fingerprint,
            # so they cannot safely suppress a proposal for
            # the current incident state.
            #
            if not existing_fingerprint:
                continue

            if (
                existing_fingerprint
                != fingerprint
            ):
                continue

            return {
                "status":
                    "DECISION_HELD",

                "incident_id":
                    action_incident_id,

                "action_request":
                    record,

                "decision":
                    status,

                "created":
                    False,

                "idempotent":
                    True,

                "incident_fingerprint":
                    fingerprint,

                "reason":
                    (
                        "existing operator decision applies "
                        "to the current incident state"
                    ),

                "safety":
                    safety,
            }


        safe_action = SafeAction(
            action=action,
            target=target,
            incident_id=(
                action_incident_id
            ),
            risk=str(
                safety.get(
                    "risk"
                )
                or "UNKNOWN"
            ),
            requires_approval=True,
            rollback=str(
                safety.get(
                    "rollback"
                )
                or ""
            ),
            status="PENDING_APPROVAL",
            evidence=list(
                safety.get(
                    "evidence"
                )
                or []
            ),
        )


        request = (
            self.approval.request(
                safe_action,
                incident_fingerprint=(
                    fingerprint
                ),
            )
        )


        return {
            "status":
                "PENDING_APPROVAL",

            "incident_id":
                action_incident_id,

            "action_request":
                request,

            "created":
                True,

            "idempotent":
                False,

            "incident_fingerprint":
                fingerprint,

            "safety":
                safety,
        }
