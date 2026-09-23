class EventCorrelation:


    def normalize(
        self,
        item,
    ):

        if isinstance(item, dict):

            return {

                "title":
                    item.get(
                        "title",
                        "unknown",
                    ),

                "summary":
                    item.get(
                        "summary",
                        item.get(
                            "message",
                            "",
                        ),
                    ),

                "severity":
                    item.get(
                        "severity",
                        "warning",
                    ),

                "asset_id":
                    item.get(
                        "asset_id",
                        None,
                    ),

            }


        return {

            "title":
                getattr(
                    item,
                    "title",
                    "unknown",
                ),

            "summary":
                getattr(
                    item,
                    "summary",
                    getattr(
                        item,
                        "message",
                        "",
                    ),
                ),

            "severity":
                getattr(
                    item,
                    "severity",
                    "warning",
                ),

            "asset_id":
                getattr(
                    item,
                    "asset_id",
                    None,
                ),

        }



    def analyze(
        self,
        insights,
    ):


        events = [

            self.normalize(
                i
            )

            for i in insights

        ]



        incidents = []



        titles = [

            e["title"].lower()

            for e in events

        ]



        #
        # Resource pressure
        #

        has_memory = any(
            "memory" in t
            for t in titles
        )


        has_docker = any(
            "docker" in t
            for t in titles
        )


        if has_memory and has_docker:

            incidents.append(
                {
                    "name": "resource_pressure",

                    "confidence": 0.8,

                    "reason":
                        "Memory pressure detected together with Docker issues.",

                    "events": [

                        {
                            "title": e["title"],
                            "detail": e["summary"],
                        }

                        for e in events

                    ],

                }
            )



        #
        # Infrastructure degradation
        #

        has_infrastructure_warning = any(

            t in (
                "infrastructure warning",
                "infrastructure health",
            )

            for t in titles

        )


        operational_events = [

            e

            for e in events

            if e["title"].lower()
            not in [
                "infrastructure warning",
                "infrastructure health",
                "docker",
            ]

        ]



        if has_infrastructure_warning and (
            has_docker
            or len(operational_events) > 0
        ):


            incidents.append(
                {
                    "name":
                        "infrastructure_degradation",

                    "confidence":
                        0.6,

                    "reason":
                        "Infrastructure warning associated with operational issues.",

                    "events": [

                        {
                            "title": e["title"],
                            "detail": e["summary"],
                            "asset_id": e.get("asset_id"),
                        }

                        for e in events

                    ],

                    "asset": next(
                        (
                            e.get("asset_id")
                            for e in events
                            if e.get("asset_id")
                        ),
                        "unknown",
                    ),

                    "affected_assets": [
                        e.get("asset_id")
                        for e in events
                        if e.get("asset_id")
                    ],

                }
            )



        #
        # Storage risk
        #

        has_storage = any(

            "storage" in t

            or "disk" in t

            for t in titles

        )



        if has_storage and has_infrastructure_warning:

            incidents.append(

                {
                    "name":
                        "storage_risk",

                    "confidence":
                        0.9,

                    "reason":
                        "Storage issues combined with infrastructure warning.",

                    "events": [

                        {
                            "title": e["title"],
                            "detail": e["summary"],
                        }

                        for e in events

                    ],

                }

            )




        #
        # Service degradation
        #

        has_container_failure = any(

            "container" in e["title"].lower()
            or "failed" in e["title"].lower()
            or "failed" in e["summary"].lower()
            or "stopped" in e["title"].lower()
            or "stopped" in e["summary"].lower()
            or "down" in e["summary"].lower()

            for e in events

        )


        if has_container_failure:

            affected_assets = [
                e.get("asset_id")
                for e in events
                if e.get("asset_id")
            ]

            incidents.append(

                {
                    "name":
                        "service_degradation",

                    "confidence":
                        0.7,

                    "severity":
                        "MEDIUM",

                    "reason":
                        "Container service failure detected.",

                    "asset":
                        affected_assets[0]
                        if affected_assets
                        else None,

                    "affected_assets":
                        affected_assets,

                    "events":

                        [

                            {
                                "title": e["title"],

                                "detail": e["summary"],

                                "asset_id": e["asset_id"],

                            }

                            for e in events

                        ],

                }

            )


        return incidents
