from atlas.storage.database import Database


class IncidentLifecycleRepository:


    def __init__(
        self,
    ):

        self.database = Database()



    def save(
        self,
        record,
    ):

        return self.database.save_incident_lifecycle(
            record
        )



    def has_fingerprint(
        self,
        incident_id,
        state,
        fingerprint,
    ):

        return (
            self.database
            .has_incident_lifecycle_fingerprint(
                incident_id,
                state,
                fingerprint,
            )
        )



    def get_by_incident(
        self,
        incident_id,
    ):

        return self.database.get_incident_lifecycle(
            incident_id
        )
