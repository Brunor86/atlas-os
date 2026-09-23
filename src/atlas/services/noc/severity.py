class SeverityEngine:


    def calculate(
        self,
        incident,
    ):

        score = 0


        confidence = getattr(
            incident,
            "confidence",
            0,
        )


        blast_radius = getattr(
            incident,
            "blast_radius",
            []
        )


        events = getattr(
            incident,
            "events",
            []
        )


        health = getattr(
            incident,
            "health",
            None
        )


        #
        # RCA confidence
        #

        if confidence >= 0.8:

            score += 30

        elif confidence >= 0.5:

            score += 15



        #
        # Dependency impact
        #

        impact_size = len(
            blast_radius
        )


        if impact_size >= 3:

            score += 40

        elif impact_size >= 1:

            score += 20



        #
        # Critical events
        #

        for event in events:


            title = ""


            if isinstance(event, dict):

                title = event.get(
                    "title",
                    ""
                ).lower()


            if "critical" in title:

                score += 30


            if "stopped" in title:

                score += 20



        #
        # Health state
        #

        if health == "critical":

            score += 30


        elif health == "degraded":

            score += 10



        #
        # Final mapping
        #

        if score >= 70:

            return "CRITICAL"


        if score >= 45:

            return "HIGH"


        if score >= 20:

            return "MEDIUM"


        return "LOW"
