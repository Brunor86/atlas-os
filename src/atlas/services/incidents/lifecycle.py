from datetime import datetime, timezone
import uuid


class IncidentLifecycle:


    def __init__(
        self,
        repository=None,
    ):

        self.repository = repository



    def transition(
        self,
        incident,
        state,
        detail="",
        *,
        persist=True,
        fingerprint=None,
    ):

        # Prefer the persistent incident identifier (INC-xxxx).
        #
        # NOCIncident.id is an internal UUID and must NOT be used
        # as the persisted lifecycle incident identifier once the
        # IncidentManager has assigned incident.incident_id.
        incident_id = getattr(
            incident,
            "incident_id",
            None
        )


        if not incident_id:

            incident_id = getattr(
                incident,
                "id",
                "unknown"
            )


        if not hasattr(
            incident,
            "lifecycle"
        ):

            incident.lifecycle = []


        #
        # Automatic NOC transitions are material-state
        # idempotent.
        #
        # Human/operator lifecycle events normally do not supply
        # a fingerprint and therefore retain the historical
        # append-only behavior.
        #
        if (
            persist
            and fingerprint
            and self.repository
        ):

            checker = getattr(
                self.repository,
                "has_fingerprint",
                None,
            )

            if (
                callable(checker)
                and checker(
                    incident_id,
                    state,
                    fingerprint,
                )
            ):

                return incident.lifecycle


        event = {

            "id":
                str(uuid.uuid4()),


            "incident_id":
                incident_id,


            "state":
                state,


            "timestamp":
                datetime.now(
                    timezone.utc
                ).isoformat(),


            "detail":
                detail,


            "actor":
                "ATLAS",

        }


        if fingerprint:

            event[
                "fingerprint"
            ] = fingerprint


        incident.lifecycle.append(
            event
        )


        if (
            persist
            and self.repository
        ):

            try:

                self.repository.save(
                    event
                )


            except Exception as exc:

                print(
                    "Lifecycle persistence error:",
                    exc
                )


        return incident.lifecycle
