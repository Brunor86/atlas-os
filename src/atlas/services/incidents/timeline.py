from atlas.storage.incident_lifecycle_repository import (
    IncidentLifecycleRepository,
)


class IncidentTimelineService:
    def __init__(self):
        self.repository = IncidentLifecycleRepository()

    def get(
        self,
        incident_id: str,
    ):
        timeline = self.repository.get_by_incident(
            incident_id
        )

        return sorted(
            timeline,
            key=lambda x: x["timestamp"],
        )
