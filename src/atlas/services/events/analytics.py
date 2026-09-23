from datetime import datetime

from atlas.storage.database import Database


class EventAnalytics:


    def __init__(self):

        self.database = Database()



    def summary(self):

        events = self.database.get_events(
            limit=1000
        )


        total = len(events)


        active = len(
            [
                e
                for e in events
                if e["status"] == "open"
            ]
        )


        closed = len(
            [
                e
                for e in events
                if e["status"] == "closed"
            ]
        )


        return {

            "total": total,

            "active": active,

            "closed": closed,

        }



    def top_events(
        self,
        limit=5,
    ):

        events = self.database.get_events(
            limit=1000
        )


        events.sort(
            key=lambda x: x["occurrences"],
            reverse=True,
        )


        return events[:limit]



    def by_category(self):

        events = self.database.get_events(
            limit=1000
        )


        result = {}


        for event in events:

            category = self.detect_category(
                event
            )


            if category not in result:

                result[category] = 0


            result[category] += 1


        return result



    def detect_category(
        self,
        event,
    ):

        title = event.get(
            "title",
            ""
        ).lower()


        message = event.get(
            "message",
            ""
        ).lower()


        text = (
            title
            + " "
            + message
        )



        if "docker" in text:

            return "docker"



        if (
            "disk" in text
            or "storage" in text
            or "filesystem" in text
        ):

            return "storage"



        if "network" in text:

            return "network"



        if "proxmox" in text:

            return "proxmox"



        return "system"



    def average_duration(self):

        events = self.database.get_events(
            limit=1000
        )


        durations = []


        for event in events:

            try:

                start = datetime.fromisoformat(
                    event["first_seen"]
                )


                end = datetime.fromisoformat(
                    event["last_seen"]
                )


                seconds = (
                    end - start
                ).total_seconds()


                durations.append(
                    seconds
                )


            except Exception:

                continue



        if not durations:

            return 0



        return sum(durations) / len(durations)



    def format_duration(
        self,
        seconds,
    ):

        seconds = int(seconds)


        if seconds < 60:

            return f"{seconds}s"



        minutes = seconds // 60


        if minutes < 60:

            return f"{minutes}m"



        hours = minutes // 60

        minutes = minutes % 60


        if hours < 24:

            return f"{hours}h {minutes}m"



        days = hours // 24

        hours = hours % 24


        return f"{days}d {hours}h"



    def average_duration_human(self):

        seconds = self.average_duration()


        return self.format_duration(
            seconds
        )



    def daily_trend(self):

        events = self.database.get_events(
            limit=1000
        )


        result = {}


        for event in events:

            try:

                date = datetime.fromisoformat(
                    event["first_seen"]
                ).date().isoformat()


                if date not in result:

                    result[date] = 0


                result[date] += 1


            except Exception:

                continue



        return result
