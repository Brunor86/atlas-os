from atlas.models.action import SafeAction


class SafeActionBuilder:

    def build(
        self,
        recommendation,
    ):

        if not recommendation:
            return None

        action = recommendation.get(
            "action"
        )

        if not action:
            return None

        return SafeAction(

            action=action,

            target=recommendation.get(
                "target",
                "infrastructure",
            ),

            incident_id=recommendation.get(
                "incident_id",
                "",
            ),

            risk=recommendation.get(
                "risk",
                "UNKNOWN",
            ),

            requires_approval=recommendation.get(
                "requires_approval",
                True,
            ),

            rollback=recommendation.get(
                "rollback",
                "",
            ),

            status=recommendation.get(
                "status",
                "PENDING_APPROVAL",
            ),

            evidence=recommendation.get(
                "evidence",
                [],
            ),

        )
