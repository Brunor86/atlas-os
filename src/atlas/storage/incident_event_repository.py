from atlas.storage.database import Database


class IncidentEventRepository:


    def __init__(self):

        self.database = Database()



    def save(
        self,
        incident_id,
        timestamp,
        event_type,
        detail="",
        severity=None,
        impact=None,
    ):

        return self.database.save_incident_event(
            incident_id,
            timestamp,
            event_type,
            detail,
            severity,
            impact,
        )



    def get_by_incident(
        self,
        incident_id,
    ):

        return self.database.get_incident_events(
            incident_id
        )
