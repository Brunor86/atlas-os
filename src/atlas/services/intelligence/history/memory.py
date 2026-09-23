from datetime import datetime, UTC


class IncidentMemory:


    def __init__(
        self,
        repository=None,
    ):

        self.repository = repository

        self.store = {}



    def remember(
        self,
        incident,
    ):

        asset = getattr(
            incident,
            "asset",
            "unknown",
        )


        if asset not in self.store:

            self.store[asset] = []



        self.store[asset].append(

            {
                "timestamp":
                    datetime.now(UTC).isoformat(),

                "root_cause":
                    getattr(
                        incident,
                        "root_cause",
                        ""
                    ),

                "severity":
                    getattr(
                        incident,
                        "severity",
                        "UNKNOWN"
                    ),

                "actions":
                    getattr(
                        incident,
                        "suggested_actions",
                        []
                    ),
            }

        )


        return self.store[asset]



    def recall(
        self,
        asset,
    ):

        return self.store.get(
            asset,
            []
        )



    def recall_history(
        self,
        incident,
    ):

        if not self.repository:

            return []


        return self.repository.get_similar_incidents(
            incident.asset,
            incident.root_cause,
        )

