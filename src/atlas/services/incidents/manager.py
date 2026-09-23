from datetime import datetime, UTC

from atlas.models.incident import Incident
from atlas.storage.incident_repository import IncidentRepository
from atlas.storage.incident_event_repository import IncidentEventRepository
from atlas.storage.incident_lifecycle_repository import IncidentLifecycleRepository
from atlas.services.incidents.lifecycle import IncidentLifecycle


class IncidentManager:


    def __init__(self):

        self.repository = IncidentRepository()

        self.event_repository = IncidentEventRepository()

        self.lifecycle_repository = IncidentLifecycleRepository()

        self.lifecycle = IncidentLifecycle(
            self.lifecycle_repository
        )



    def create_from_issue(
        self,
        issue,
    ):

        existing = self.find_open(
            issue
        )


        if existing:
            return self.to_incident(existing)



        incident = Incident(

            id=self.next_id(),

            title=issue.name,

            asset=getattr(
                issue,
                "asset",
                "unknown"
            ),

            severity=getattr(
                issue,
                "severity",
                "LOW",
            ),

            status="OPEN",

            evidence=getattr(
                issue,
                "signals",
                []
            ),

            recommendations=[],

        )


        # Persistent operational identity.
        #
        # Incident.id is the authoritative INC-xxxx identifier.
        # Lifecycle must use it from the very first transition.
        incident.incident_id = incident.id

        self.repository.save(
            incident
        )


        self.lifecycle.transition(
            incident,
            "OPEN",
            "Incident created from NOC issue",
        )


        self.add_event(
            incident.id,
            "CREATED",
            "Incident created from NOC issue",
            incident.severity,
            getattr(issue, "impact", []),
        )


        return incident





    def find_open(
        self,
        issue,
    ):

        incidents = self.repository.get_all()

        title = getattr(
            issue,
            "name",
            "",
        )

        asset = getattr(
            issue,
            "asset",
            "unknown",
        )

        for incident in incidents:

            incident_title = incident[1]
            incident_asset = incident[2]
            incident_status = incident[4]

            if incident_status in (
                "CLOSED",
                "RESOLVED",
            ):
                continue

            # mismo tipo de incidente
            if incident_title == title:
                return incident

            # mismo asset afectado
            if (
                asset != "unknown"
                and incident_asset == asset
            ):
                return incident

        return None

    def next_id(
        self,
    ):

        incidents = self.repository.get_all()

        number = len(incidents) + 1

        return f"INC-{number:04d}"





    def update_status(
        self,
        incident_id,
        status,
    ):

        return self.repository.update_status(

            incident_id,

            status,

            datetime.now(UTC).isoformat(),

        )





    def resolve(
        self,
        incident_id,
    ):

        return self.repository.update_status(

            incident_id,

            "RESOLVED",

            datetime.now(UTC).isoformat(),

        )






    def sync_incident(
        self,
        issue,
    ):

        existing = self.find_open(
            issue
        )

        #
        # Persistent operational identity.
        #
        # The NOC UUID (`issue.id`) is internal.
        # The IncidentManager identifier (`INC-xxxx`) is
        # authoritative for lifecycle, context and AI reasoning.
        #

        if existing:

            issue.incident_id = existing[0]


        impact = getattr(
            issue,
            "impact",
            [],
        )


        root_cause = getattr(
            issue,
            "root_cause",
            "",
        )


        diagnosis = getattr(
            issue,
            "diagnosis",
            "",
        )


        blast_radius = getattr(
            issue,
            "blast_radius",
            [],
        )


        suggested_actions = getattr(
            issue,
            "suggested_actions",
            [],
        )


        if isinstance(issue, dict):

            impact_intelligence = issue.get(
                "impact_intelligence",
                {},
            )

        else:

            impact_intelligence = getattr(
                issue,
                "impact_intelligence",
                {},
            )


        events = getattr(
            issue,
            "events",
            [],
        )


        if existing:

            previous_severity = existing[3]

            # get_incidents() layout:
            #
            # 0  id
            # 1  title
            # 2  asset
            # 3  severity
            # 4  status
            # 5  evidence
            # 6  recommendations
            # 7  impact
            # 8  created_at
            # 9  updated_at
            # 10 root_cause
            # 11 diagnosis
            # 12 blast_radius
            # 13 suggested_actions
            # 14 impact_intelligence

            previous_impact = existing[7]

            asset = (
                getattr(
                    issue,
                    "asset",
                    None,
                )
                or "unknown"
            )


            self.repository.update(

                existing[0],

                asset,

                issue.severity,

                events,

                impact,

                impact_intelligence,

                root_cause,

                diagnosis,

                blast_radius,

                suggested_actions,

                datetime.now(UTC).isoformat(),

            )


            if previous_severity != issue.severity:

                self.add_event(

                    existing[0],

                    "SEVERITY_CHANGED",

                    (
                        f"Severity changed "
                        f"{previous_severity} -> "
                        f"{issue.severity}"
                    ),

                    issue.severity,

                    impact,

                )


            if str(previous_impact) != str(impact):

                self.add_event(

                    existing[0],

                    "IMPACT_UPDATED",

                    "Incident impact updated",

                    issue.severity,

                    impact,

                )


            return issue.incident_id


        created = self.create_from_issue(
            issue
        )

        if created:
            # create_from_issue() creates the authoritative
            # persistent Incident identifier.
            issue.incident_id = created.id

        return issue.incident_id


    def add_event(
        self,
        incident_id,
        event_type,
        detail="",
        severity=None,
        impact=None,
    ):

        return self.event_repository.save(

            incident_id,

            datetime.now(UTC).isoformat(),

            event_type,

            detail,

            severity,

            impact,

        )





    def get_incident(
        self,
        incident_id,
    ):

        incidents = self.repository.get_all()

        for row in incidents:

            if row[0] == incident_id:

                return self.to_incident(
                    row
                )

        return None


    def to_incident(
        self,
        row,
    ):

        import ast

        def parse(value):
            if not value:
                return []
            try:
                return ast.literal_eval(value)
            except Exception:
                return value


        incident = Incident(

            id=row[0],

            title=row[1],

            asset=row[2],

            severity=row[3],

            status=row[4],

            evidence=parse(row[5]),

            recommendations=parse(row[6]),

            impact=parse(row[7]),

            impact_intelligence=parse(row[8]),

            root_cause=row[9] or "",

            diagnosis=row[10] or "",

            blast_radius=parse(row[11]),

            suggested_actions=parse(row[12]),

        )

        # Restore the authoritative persistent Incident identity.
        #
        # Incident.id is already the persistent INC-xxxx identifier.
        # Keep incident_id synchronized when reconstructing the object
        # from SQLite so lifecycle transitions never fall back to the
        # internal NOCIncident UUID.
        incident.incident_id = incident.id

        return incident
