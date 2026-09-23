from datetime import (
    UTC,
    datetime,
)

from atlas.services.incidents.manager import (
    IncidentManager,
)

from atlas.storage.action_repository import (
    ActionRepository,
)


class IncidentRecoveryService:
    """
    Reconcile persistent incident status with incidents detected
    by one complete authoritative operational cycle.

    State machine:

        OPEN
          |
          | absent once
          v
        RECOVERING
          |
          | still absent after grace
          v
        RESOLVED

    If a RECOVERING incident reappears before confirmation,
    it returns to OPEN.

    RESOLVED incidents are historical. A later recurrence is
    expected to receive a new persistent incident identity.
    """

    RECOVERY_GRACE_SECONDS = 300

    MANAGED_STATUSES = {
        "OPEN",
        "RECOVERING",
    }


    def __init__(
        self,
        incident_manager=None,
        action_repository=None,
        clock=None,
    ):

        self.manager = (
            incident_manager
            or IncidentManager()
        )

        self.action_repository = (
            action_repository
            or ActionRepository(
                self.manager
                .repository
                .database
            )
        )

        self.clock = (
            clock
            or (
                lambda:
                    datetime.now(
                        UTC
                    )
            )
        )


    @staticmethod
    def _normalize(
        value,
    ):

        return str(
            value
            or ""
        ).strip().upper()


    @staticmethod
    def _incident_id(
        incident,
    ):

        if isinstance(
            incident,
            dict,
        ):

            value = (
                incident.get(
                    "incident_id"
                )
                or incident.get(
                    "id"
                )
            )

        else:

            value = (
                getattr(
                    incident,
                    "incident_id",
                    None,
                )
                or getattr(
                    incident,
                    "id",
                    None,
                )
            )

        value = str(
            value
            or ""
        ).strip()

        return (
            value
            or None
        )


    @staticmethod
    def _parse_timestamp(
        value,
    ):

        if not value:
            return None

        parsed = datetime.fromisoformat(
            str(value)
        )

        if parsed.tzinfo is None:

            parsed = parsed.replace(
                tzinfo=UTC
            )

        return parsed


    def _age_seconds(
        self,
        timestamp,
    ):

        parsed = self._parse_timestamp(
            timestamp
        )

        if parsed is None:
            return None

        return max(
            0,
            int(
                (
                    self.clock()
                    - parsed
                ).total_seconds()
            ),
        )


    def _persist_transition(
        self,
        incident_id,
        status,
        *,
        event_type,
        detail,
    ):

        incident = (
            self.manager.get_incident(
                incident_id
            )
        )

        if incident is None:

            raise ValueError(
                f"Incident not found: "
                f"{incident_id}"
            )

        self.manager.update_status(
            incident_id,
            status,
        )

        incident.status = status

        self.manager.add_event(
            incident_id,
            event_type,
            detail,
            incident.severity,
            incident.impact,
        )

        self.manager.lifecycle.transition(
            incident,
            status,
            detail,
        )


    def reconcile(
        self,
        current_incidents,
        *,
        authoritative=True,
    ):

        if not authoritative:

            return {
                "status":
                    "SKIPPED",

                "reason":
                    "NON_AUTHORITATIVE",

                "transitions":
                    [],
            }


        current_ids = {
            incident_id

            for incident_id
            in (
                self._incident_id(
                    incident
                )
                for incident
                in (
                    current_incidents
                    or []
                )
            )

            if incident_id
        }


        records = (
            self.manager
            .repository
            .get_all_records()
        )

        transitions = []


        for record in records:

            incident_id = str(
                record.get(
                    "id",
                    ""
                )
                or ""
            ).strip()

            status = self._normalize(
                record.get(
                    "status"
                )
            )


            if (
                not incident_id
                or status
                not in self.MANAGED_STATUSES
            ):
                continue


            present = (
                incident_id
                in current_ids
            )


            #
            # Recovery interrupted:
            # the exact persistent incident identity has
            # reappeared in the authoritative NOC result.
            #
            if present:

                if status == "RECOVERING":

                    self._persist_transition(
                        incident_id,
                        "OPEN",
                        event_type=
                            "RECOVERY_ABORTED",
                        detail=(
                            "Incident condition "
                            "reappeared during "
                            "recovery confirmation"
                        ),
                    )

                    transitions.append(
                        {
                            "incident_id":
                                incident_id,

                            "from":
                                "RECOVERING",

                            "to":
                                "OPEN",

                            "reason":
                                "CONDITION_REAPPEARED",
                        }
                    )

                continue


            #
            # First complete authoritative cycle without
            # this incident.
            #
            if status == "OPEN":

                cancelled = (
                    self.action_repository
                    .cancel_unexecuted_actions_for_incident(
                        incident_id
                    )
                )

                self._persist_transition(
                    incident_id,
                    "RECOVERING",
                    event_type=
                        "RECOVERY_STARTED",
                    detail=(
                        "Incident condition absent "
                        "from authoritative cycle"
                    ),
                )

                transitions.append(
                    {
                        "incident_id":
                            incident_id,

                        "from":
                            "OPEN",

                        "to":
                            "RECOVERING",

                        "reason":
                            "CONDITION_ABSENT",

                        "cancelled_actions":
                            cancelled,
                    }
                )

                continue


            #
            # RECOVERING must survive the grace period before
            # becoming RESOLVED. This prevents an immediate
            # manual second cycle from falsely confirming
            # recovery.
            #
            age = self._age_seconds(
                record.get(
                    "updated_at"
                )
            )

            if (
                age is None
                or age
                < self.RECOVERY_GRACE_SECONDS
            ):
                continue


            cancelled = (
                self.action_repository
                .cancel_unexecuted_actions_for_incident(
                    incident_id
                )
            )

            self._persist_transition(
                incident_id,
                "RESOLVED",
                event_type=
                    "RESOLVED",
                detail=(
                    "Incident condition remained "
                    "absent through recovery "
                    "confirmation window"
                ),
            )

            transitions.append(
                {
                    "incident_id":
                        incident_id,

                    "from":
                        "RECOVERING",

                    "to":
                        "RESOLVED",

                    "reason":
                        "RECOVERY_CONFIRMED",

                    "cancelled_actions":
                        cancelled,
                }
            )


        return {
            "status":
                "SUCCESS",

            "authoritative":
                True,

            "current_incidents":
                sorted(
                    current_ids
                ),

            "transitions":
                transitions,
        }
