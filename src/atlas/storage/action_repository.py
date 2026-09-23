class ActionRepository:


    def __init__(
        self,
        database,
    ):

        self.database = database



    def save_action_request(
        self,
        action,
    ):

        return self.database.save_action_request(
            action
        )



    def update_action_status(
        self,
        action_id,
        status,
        user,
    ):

        return self.database.update_action_status(
            action_id,
            status,
            user,
        )



    def get_pending_actions(
        self,
    ):

        return self.database.get_pending_actions()


    def list_action_requests(
        self,
        limit=50,
    ):

        return (
            self.database
            .list_action_requests(
                limit=limit
            )
        )


    def mark_action_executed(
        self,
        action_id,
    ):

        return self.database.mark_action_executed(
            action_id
        )



    def get_action_request(
        self,
        action_id,
    ):

        return self.database.get_action_request(
            action_id
        )



    def get_action_requests_by_incident(
        self,
        incident_id,
    ):

        return (
            self.database
            .get_action_requests_by_incident(
                incident_id
            )
        )


    def update_action_fingerprint(
        self,
        action_id,
        incident_fingerprint,
    ):

        return (
            self.database
            .update_action_fingerprint(
                action_id,
                incident_fingerprint,
            )
        )


    def cancel_unexecuted_actions_for_incident(
        self,
        incident_id,
    ):

        return (
            self.database
            .cancel_unexecuted_actions_for_incident(
                incident_id
            )
        )


    def set_action_status(
        self,
        action_id,
        status,
    ):

        return (
            self.database
            .set_action_status(
                action_id,
                status,
            )
        )


    def finalize_action_verification(
        self,
        record,
        action_status,
        *,
        expected_current_status=None,
    ):

        return (
            self.database
            .finalize_action_verification(
                record,
                action_status,
                expected_current_status=(
                    expected_current_status
                ),
            )
        )


    def get_action_verification(
        self,
        approval_id,
    ):

        return (
            self.database
            .get_action_verification(
                approval_id
            )
        )


    def get_action_verification_history(
        self,
        approval_id,
    ):

        return (
            self.database
            .get_action_verification_history(
                approval_id
            )
        )


    def save_learning(
        self,
        record,
    ):

        return (
            self.database
            .save_learning(
                record
            )
        )


    def save_action_history(
        self,
        execution,
    ):

        return self.database.save_action_history(
            execution
        )



    def get_action_history(
        self,
    ):

        return self.database.get_action_history()


    def claim_action_execution(self, approval_id):
        return self.database.claim_action_execution(approval_id)


    def get_action_execution_state(
        self,
        approval_id,
    ):

        return (
            self.database
            .get_action_execution_state(
                approval_id
            )
        )


    def has_action_been_executed(
        self,
        approval_id,
    ):

        history = (
            self.database
            .get_action_history()
        )

        for record in history:

            if isinstance(
                record,
                dict,
            ):
                record_approval_id = (
                    record.get(
                        "approval_id"
                    )
                )

            elif isinstance(
                record,
                (tuple, list),
            ) and len(record) > 1:

                record_approval_id = (
                    record[1]
                )

            else:
                continue

            if (
                record_approval_id
                == approval_id
            ):
                return True

        return False
