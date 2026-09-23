from atlas.services.intelligence.execution.service import (
    ActionExecutionService,
)

from atlas.services.intelligence.verification.service import (
    ActionVerificationService,
)


class ActionExecutorService:

    def __init__(
        self,
        repository=None,
        learning_repository=None,
        verification=None,
    ):

        self.repository = repository

        self.learning_repository = (
            learning_repository
        )

        self.execution = ActionExecutionService(
            repository,
            learning_repository,
        )

        self.verification = (
            verification
            or ActionVerificationService()
        )


    def _verification_capable(
        self,
    ):

        return bool(
            self.repository
            and callable(
                getattr(
                    self.repository,
                    "finalize_action_verification",
                    None,
                )
            )
            and callable(
                getattr(
                    self.repository,
                    "set_action_status",
                    None,
                )
            )
        )


    def _learn(
        self,
        execution,
        result,
        resolution,
        evidence,
    ):

        self.execution.learning.learn(
            incident_id=
                execution.incident_id,

            action=
                execution.action,

            result=
                result,

            resolution=
                resolution,

            evidence=
                evidence,
        )


    def execute(
        self,
        approval,
    ):

        if not approval:
            return {
                "status": "BLOCKED",
                "reason": [
                    "approval is required",
                ],
                "approval_id": None,
            }


        approval_id = approval.get(
            "id",
            "",
        )


        if not approval_id:
            return {
                "status": "BLOCKED",
                "reason": [
                    "approval id is required",
                ],
                "approval_id": None,
            }


        status = approval.get(
            "status"
        )


        if status not in (
            "APPROVED",
            "AUTO_APPROVED",
        ):
            return {
                "status": "BLOCKED",
                "reason": [
                    "action requires approval",
                ],
                "approval_id": approval_id,
            }


        #
        # Approval integrity.
        #
        persisted = None

        if self.repository:

            persisted = (
                self.repository
                .get_action_request(
                    approval_id
                )
            )


        if persisted is None:
            return {
                "status": "BLOCKED",
                "reason": [
                    "approval does not exist",
                ],
                "approval_id": approval_id,
            }


        if persisted.get(
            "status"
        ) not in (
            "APPROVED",
            "AUTO_APPROVED",
        ):
            return {
                "status": "BLOCKED",
                "reason": [
                    "persisted approval is not executable",
                ],
                "approval_id": approval_id,
            }


        for field in (
            "incident_id",
            "action",
            "target",
            "risk",
            "rollback",
        ):

            supplied = approval.get(
                field
            )

            stored = persisted.get(
                field
            )

            if (
                supplied is not None
                and supplied != stored
            ):

                return {
                    "status": "BLOCKED",
                    "reason": [
                        (
                            "approval "
                            + field
                            + " does not match "
                            "persisted record"
                        )
                    ],
                    "approval_id":
                        approval_id,
                }


        #
        # Replay protection.
        #
        if (
            self.repository
            and hasattr(
                self.repository,
                "has_action_been_executed",
            )
        ):

            if (
                self.repository
                .has_action_been_executed(
                    approval_id
                )
            ):

                return {
                    "status":
                        "BLOCKED",

                    "reason": [
                        "approval has already been executed",
                    ],

                    "approval_id":
                        approval_id,
                }


        claim = getattr(
            self.repository,
            "claim_action_execution",
            None,
        )


        if not callable(
            claim
        ):

            return {
                "status":
                    "BLOCKED",

                "reason": [
                    (
                        "repository cannot atomically "
                        "reserve execution"
                    )
                ],

                "approval_id":
                    approval_id,
            }


        try:

            claimed = claim(
                approval_id
            )

        except Exception:

            return {
                "status":
                    "BLOCKED",

                "reason": [
                    (
                        "execution reservation "
                        "could not be confirmed"
                    )
                ],

                "approval_id":
                    approval_id,
            }


        if claimed is not True:

            return {
                "status":
                    "BLOCKED",

                "reason": [
                    (
                        "approval is already reserved "
                        "or no longer executable"
                    )
                ],

                "approval_id":
                    approval_id,
            }


        #
        # The durable claim is intentionally never released.
        #
        execution = (
            self.execution.execute(
                persisted
            )
        )


        #
        # Compatibility path for lightweight test/legacy
        # repositories without verification persistence.
        #
        if not self._verification_capable():

            return execution


        #
        # Command did not establish a successful execution.
        #
        if (
            getattr(
                execution,
                "status",
                None,
            )
            != "SUCCESS"
        ):

            self.repository.set_action_status(
                approval_id,
                "EXECUTION_FAILED",
            )

            self._learn(
                execution,
                "EXECUTION_FAILED",
                str(
                    getattr(
                        execution,
                        "result",
                        "",
                    )
                ),
                list(
                    getattr(
                        execution,
                        "evidence",
                        [],
                    )
                    or []
                ),
            )

            return execution


        #
        # Independent post-execution state verification.
        #
        try:

            verification = (
                self.verification.verify(
                    persisted.get(
                        "action",
                        ""
                    ),
                    persisted.get(
                        "target",
                        ""
                    ),
                )
            )


        except Exception as exc:

            verification = {
                "status":
                    "RECOVERY_REQUIRED",

                "action":
                    persisted.get(
                        "action",
                        ""
                    ),

                "target":
                    persisted.get(
                        "target",
                        ""
                    ),

                "expected_state":
                    "known",

                "observed_state":
                    "unknown",

                "detail":
                    (
                        "post-execution verifier "
                        "raised: "
                        + str(exc)
                    ),

                "evidence": [
                    "verification fails closed",
                ],

                "verified_at":
                    getattr(
                        execution,
                        "executed_at",
                        "",
                    ),
            }


        verification_status = str(
            verification.get(
                "status",
                ""
            )
            or ""
        ).strip().upper()


        if (
            verification_status
            != "VERIFIED"
        ):

            verification_status = (
                "RECOVERY_REQUIRED"
            )

            verification[
                "status"
            ] = verification_status


        final_action_status = (
            verification_status
        )


        record = {
            "approval_id":
                approval_id,

            "status":
                verification_status,

            "action":
                persisted.get(
                    "action",
                    ""
                ),

            "target":
                persisted.get(
                    "target",
                    ""
                ),

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
                    ""
                ),

            "evidence":
                list(
                    verification.get(
                        "evidence",
                        []
                    )
                    or []
                ),

            "verified_at":
                verification.get(
                    "verified_at"
                )
                or getattr(
                    execution,
                    "executed_at",
                    "",
                ),
        }


        self.repository.finalize_action_verification(
            record,
            final_action_status,
        )


        execution.verification = dict(
            record
        )


        combined_evidence = (
            list(
                getattr(
                    execution,
                    "evidence",
                    [],
                )
                or []
            )
            + list(
                record[
                    "evidence"
                ]
            )
        )


        self._learn(
            execution,
            verification_status,
            (
                record[
                    "detail"
                ]
                or str(
                    getattr(
                        execution,
                        "result",
                        "",
                    )
                )
            ),
            combined_evidence,
        )


        return execution
