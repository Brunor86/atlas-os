from atlas.storage.database import Database


class EventRepository:


    def __init__(self):

        self.database = Database()



    def get_active_events(self):

        return self.database.get_active_events()



    def get_recent_events(
        self,
        limit=20,
    ):

        return self.database.get_events(
            limit
        )



    def count_active_events(self):

        events = self.database.get_active_events()

        return len(events)



    def count_by_severity(self):

        events = self.database.get_active_events()


        result = {}


        for event in events:

            severity = event.get(
                "severity",
                "unknown",
            )

            result[severity] = (
                result.get(
                    severity,
                    0,
                )
                + 1
            )


        return result
