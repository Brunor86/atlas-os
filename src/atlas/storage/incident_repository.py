from atlas.storage.database import Database
from atlas.storage.incident_event_repository import IncidentEventRepository


class IncidentRepository:


    def __init__(self):

        self.database = Database()

        self.event_repository = IncidentEventRepository()



    def save_learning(
        self,
        record,
    ):

        return self.database.save_learning(
            record
        )




    def get_learning_records(
        self,
    ):

        return self.database.get_learning_records()





    def get_successful_learning_actions(
        self,
    ):

        return self.database.get_successful_learning_actions()




    def get_event_history(
        self,
        incident_id,
    ):

        return self.event_repository.get_by_incident(
            incident_id
        )



    def save(
        self,
        incident,
    ):

        return self.database.save_incident(
            incident
        )



    @staticmethod
    def _record(
        row,
    ):
        """
        Normalize the historical database tuple contract into a stable
        incident record for semantic/read-only consumers.

        Existing tuple-returning methods remain untouched for backwards
        compatibility.
        """

        if row is None:
            return None

        if isinstance(
            row,
            dict,
        ):
            return dict(
                row
            )

        return {
            "id":
                row[0],

            "title":
                row[1],

            "asset_id":
                row[2],

            "severity":
                row[3],

            "status":
                row[4],

            "evidence":
                row[5],

            "recommendations":
                row[6],

            "impact":
                row[7],

            "impact_intelligence":
                row[8],

            "root_cause":
                row[9],

            "diagnosis":
                row[10],

            "blast_radius":
                row[11],

            "suggested_actions":
                row[12],

            "created_at":
                row[13],

            "updated_at":
                row[14],
        }


    def get_all(self):

        return self.database.get_incidents()


    def get_all_records(
        self,
    ):

        return [
            record

            for record in (
                self._record(
                    row
                )

                for row in self.get_all()
            )

            if record is not None
        ]


    def get_active_records(
        self,
    ):

        closed = {
            "RESOLVED",
            "CLOSED",
            "CANCELLED",
            "CANCELED",
        }

        return [
            record

            for record
            in self.get_all_records()

            if str(
                record.get(
                    "status"
                )
                or ""
            ).upper()
            not in closed
        ]



    def find_active(
        self,
        title,
        asset,
    ):

        return self.database.find_active_incident(
            title,
            asset,
        )



    def update(
        self,
        incident_id,
        asset,
        severity,
        evidence,
        impact,

          impact_intelligence,
        root_cause,
        diagnosis,
        blast_radius,
        suggested_actions,
        updated_at,
    ):

        return self.database.update_incident(
            incident_id,
            asset,
            severity,
            evidence,
            impact,

              impact_intelligence,
            root_cause,
            diagnosis,
            blast_radius,
            suggested_actions,
            updated_at,
        )



    def update_status(
        self,
        incident_id,
        status,
        updated_at,
    ):

        return self.database.update_incident_status(
            incident_id,
            status,
            updated_at,
        )


    def count_by_status(
        self,
        status,
    ):

        return self.database.count_incidents_by_status(
            status
        )



    def count_by_severity(
        self,
        severity,
    ):

        return self.database.count_incidents_by_severity(
            severity
        )



    def count_by_title(
        self,
    ):

        return self.database.count_incidents_by_title()



    def find_history(
        self,
        title,
        asset,
    ):

        return self.database.find_incident_history(
            title,
            asset,
        )



    def get_similar_incidents(
        self,
        asset,
        root_cause,
    ):

        return self.database.get_similar_incidents(
            asset,
            root_cause,
        )
