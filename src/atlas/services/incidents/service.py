from datetime import datetime, UTC

from atlas.models.incident import Incident
from atlas.storage.incident_repository import IncidentRepository
from atlas.services.incidents.analytics import IncidentAnalytics
from atlas.services.incidents.timeline import IncidentTimelineService



class IncidentService:


    def __init__(self):

        self.repository = IncidentRepository()

        self.analytics = IncidentAnalytics()

        self.timeline_service = IncidentTimelineService()



    def create(
        self,
        title: str,
        asset: str,
        severity: str,
        evidence=None,
        recommendations=None,
    ) -> Incident:


        incident = Incident(

            id=self._next_id(),

            title=title,

            asset=asset,

            severity=severity,

            evidence=evidence or [],

            recommendations=recommendations or [],

        )


        self.repository.save(
            incident
        )


        return incident



    def _next_id(self):

        incidents = self.repository.get_all()


        number = len(incidents) + 1


        return f"INC-{number:04d}"



    def create_or_update(
        self,
        title: str,
        asset: str,
        severity: str,
        evidence=None,
        recommendations=None,
    ):


        evidence = evidence or []

        recommendations = recommendations or []


        existing = self.repository.find_active(
            title,
            asset,
        )


        now = datetime.now(UTC).isoformat()



        if existing:


            self.repository.update(

                existing[0],

                severity,

                evidence,

                recommendations,

                now,

            )


            return existing[0]



        return self.create(

            title,

            asset,

            severity,

            evidence,

            recommendations,

        )



    def list_all(self):

        return self.repository.get_all()



    def get_open(self):

        return [

            incident

            for incident in self.repository.get_all()

            if incident[4] != "RESOLVED"

        ]



    def summary(self):

        return self.analytics.summary()



    def severity_distribution(self):

        return self.analytics.severity_distribution()



    def timeline(
        self,
        incident_id,
    ):

        return self.timeline_service.get(
            incident_id
        )



    def detail(
        self,
        incident_id,
    ):

        incidents = self.repository.get_all()


        for incident in incidents:

            if incident[0] == incident_id:

                return incident


        return None



    def update_status(
        self,
        incident_id: str,
        status: str,
    ):

        return self.repository.update_status(

            incident_id,

            status,

            datetime.now(UTC).isoformat(),

        )
