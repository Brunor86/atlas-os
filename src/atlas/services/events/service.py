import logging

from datetime import datetime

from atlas.storage.database import Database


logger = logging.getLogger(__name__)


class EventService:


    def __init__(self):

        self.database = Database()



    def process(
        self,
        insights,
    ):

        now = datetime.now().isoformat()

        current_keys = []


        for insight in insights:

            logger.debug(
                "Event insight type=%s",
                type(insight).__name__,
            )

            if hasattr(insight, "to_dict"):
                insight = insight.to_dict()

            elif hasattr(insight, "__dataclass_fields__"):
                from dataclasses import asdict
                insight = asdict(insight)

            elif hasattr(insight, "__dict__"):
                insight = insight.__dict__

            severity = self.get_severity(
                insight
            )


            event_type = str(
                insight.get(
                    "type"
                )
                or severity
                or "unknown"
            ).strip().lower()


            title = insight.get(
                "title",
                "Unknown event",
            )


            message = (
                insight.get(
                    "message"
                )
                or insight.get(
                    "summary"
                )
                or ""
            )


            asset_id = insight.get(
                "asset_id"
            )


            event_key = self.generate_key(
                insight
            )


            category = self.get_category(
                insight
            )


            current_keys.append(
                event_key
            )


            existing = self.find_open_event(
                event_key
            )


            if existing:

                self.database.refresh_event(
                    existing["id"],
                    event_type,
                    title,
                    message,
                    now,
                    severity,
                    category,
                    asset_id,
                )


            else:

                self.database.save_event(
                    event_type,
                    title,
                    message,
                    now,
                    now,
                    "open",
                    event_key,
                    severity,
                    category,
                    1,
                    asset_id,
                )



        self.close_missing_events(
            current_keys,
            now,
        )


        return insights



    def generate_key(
        self,
        insight,
    ):

        title = insight.get(
            "title",
            "unknown",
        )


        return (
            title
            .lower()
            .replace(
                " ",
                "_",
            )
        )



    def get_severity(
        self,
        insight,
    ):

        severity = str(
            insight.get(
                "severity"
            )
            or insight.get(
                "type"
            )
            or "warning"
        ).strip().lower()


        if severity in (
            "critical",
            "warning",
            "info",
        ):

            return severity


        return "warning"



    def get_category(
        self,
        insight,
    ):

        title = insight.get(
            "title",
            "",
        ).lower()


        if "docker" in title:

            return "docker"


        if "storage" in title or "disk" in title:

            return "storage"


        if "network" in title:

            return "network"


        if "proxmox" in title:

            return "proxmox"


        return "system"



    def find_open_event(
        self,
        event_key,
    ):

        events = self.database.get_active_events()


        for event in events:

            if event.get("event_key") == event_key:

                return event


        return None



    def close_missing_events(
        self,
        current_keys,
        timestamp,
    ):

        events = self.database.get_active_events()


        for event in events:

            if event.get("event_key") not in current_keys:

                self.database.close_event(
                    event["id"],
                    timestamp,
                )
