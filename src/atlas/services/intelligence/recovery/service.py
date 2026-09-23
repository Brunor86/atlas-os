from __future__ import annotations

from datetime import (
    UTC,
    datetime,
)

from atlas.services.intelligence.verification.service import (
    ActionVerificationService,
)


class ActionRecoveryService:
    """
    Manual recovery through independent re-verification.

    This service is intentionally read-only with respect to the
    infrastructure. It never re-executes the original action and never
    performs rollback automatically.

    A recovery attempt may only inspect an action already persisted as
    RECOVERY_REQUIRED after a successful execution.
    """

    def __init__(
        self,
        repository,
        verification=None,
    ):

        if repository is None:
            raise ValueError(
                "recovery repository is required"
            )

        self.repository = repository

        self.verification = (
            verification
            or ActionVerificationService()
        )


    def reverify(
        self,
        approval_id,
        *,
        requested_by,
    ):

        actor = str(
            requested_by
            or ""
        ).strip()

        if not actor:
            raise ValueError(
                "recovery operator identity is required"
            )


        action = (
            self.repository
            .get_action_request(
                approval_id
            )
        )

        if action is None:
            raise LookupError(
                "action request not found"
            )


        current_status = str(
            action.get(
                "status",
                ""
            )
            or ""
        ).strip().upper()

        if current_status != "RECOVERY_REQUIRED":
            raise ValueError(
                "action is not in RECOVERY_REQUIRED: "
                + current_status
            )


        state = (
            self.repository
            .get_action_execution_state(
                approval_id
            )
        )

        history = (
            state.get(
                "history"
            )
            if isinstance(
                state,
                dict,
            )
            else None
        )

        if (
            not state
            or state.get("state")
            != "RECOVERY_REQUIRED"
            or not history
            or history.get("status")
            != "SUCCESS"
        ):
            raise ValueError(
                "recovery requires a successfully "
                "executed action"
            )


        current_verification = (
            self.repository
            .get_action_verification(
                approval_id
            )
        )

        if (
            not current_verification
            or current_verification.get(
                "status"
            )
            != "RECOVERY_REQUIRED"
        ):
            raise ValueError(
                "recovery verification state "
                "is inconsistent"
            )


        action_name = str(
            action.get(
                "action",
                ""
            )
            or ""
        )

        target = str(
            action.get(
                "target",
                ""
            )
            or ""
        )


        try:

            verification = (
                self.verification.verify(
                    action_name,
                    target,
                )
            )

        except Exception as exc:

            verification = {
                "status":
                    "RECOVERY_REQUIRED",

                "action":
                    action_name,

                "target":
                    target,

                "expected_state":
                    current_verification.get(
                        "expected_state"
                    )
                    or "known",

                "observed_state":
                    "unknown",

                "detail":
                    (
                        "manual re-verification "
                        "raised: "
                        + str(exc)
                    ),

                "evidence": [
                    "manual re-verification "
                    "fails closed",
                ],

                "verified_at":
                    datetime.now(
                        UTC
                    ).isoformat(),
            }


        verification_status = str(
            verification.get(
                "status",
                ""
            )
            or ""
        ).strip().upper()

        if verification_status != "VERIFIED":
            verification_status = (
                "RECOVERY_REQUIRED"
            )


        record = {
            "approval_id":
                approval_id,

            "status":
                verification_status,

            "action":
                action_name,

            "target":
                target,

            "expected_state":
                verification.get(
                    "expected_state"
                ),

            "observed_state":
                verification.get(
                    "observed_state"
                ),

            "detail":
                verification.get(
                    "detail",
                    "",
                ),

            "evidence":
                list(
                    verification.get(
                        "evidence",
                        [],
                    )
                    or []
                ),

            "verified_at":
                verification.get(
                    "verified_at"
                )
                or datetime.now(
                    UTC
                ).isoformat(),

            "source":
                "MANUAL_REVERIFY",

            "requested_by":
                actor,
        }


        persisted = (
            self.repository
            .finalize_action_verification(
                record,
                verification_status,
                expected_current_status=(
                    "RECOVERY_REQUIRED"
                ),
            )
        )


        if persisted is False:
            raise ValueError(
                "recovery state changed during "
                "re-verification"
            )


        return record
