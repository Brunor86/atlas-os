from atlas.storage.incident_repository import (
    IncidentRepository,
)


class IncidentAnalytics:


    def __init__(
        self,
        repository=None,
    ):

        self.repository = (
            repository
            or IncidentRepository()
        )


    def summary(
        self,
    ):

        incidents = (
            self.repository.get_all()
        )

        active = (
            self.repository
            .get_active_records()
        )


        total = len(
            incidents
        )


        critical = sum(
            1

            for incident
            in active

            if str(
                incident.get(
                    "severity",
                    ""
                )
            ).upper()
            == "CRITICAL"
        )


        return {
            "total":
                total,

            "open":
                len(
                    active
                ),

            "critical":
                critical,

            "top_incidents":
                self.top_incidents(),
        }


    def top_incidents(
        self,
    ):

        rows = (
            self.repository
            .count_by_title()
        )


        return [
            {
                "title":
                    row[0],

                "count":
                    row[1],
            }

            for row
            in rows[:5]
        ]


    def severity_distribution(
        self,
    ):

        result = {
            "CRITICAL": 0,
            "WARNING": 0,
            "MEDIUM": 0,
            "LOW": 0,
        }


        for incident in (
            self.repository
            .get_active_records()
        ):

            severity = str(
                incident.get(
                    "severity",
                    ""
                )
                or ""
            ).upper()

            if severity in result:

                result[
                    severity
                ] += 1


        return result
