from datetime import datetime, UTC


class NOCExplanationService:


    def explain(
        self,
        incident,
        reasoning=None,
        recommendation=None,
        learning=None,
    ):

        explanations = []


        if isinstance(
            incident,
            tuple,
        ):

            name = (
                incident[1]
                if len(incident) > 1
                else "unknown"
            )

        elif isinstance(
            incident,
            dict,
        ):

            name = (
                incident.get("name")
                or incident.get("incident_type")
                or incident.get("reason")
                or "unknown"
            )

        else:

            name = getattr(
                incident,
                "name",
                "unknown"
            )


        explanations.append(
            f"Incident detected: {name}"
        )


        if reasoning:

            root = reasoning.get(
                "root_cause"
            )

            if root:

                explanations.append(
                    f"Root cause identified: {root}"
                )


        if learning:

            cases = learning.get(
                "similar_cases",
                0
            )


            confidence = learning.get(
                "confidence",
                0
            )


            if cases:

                explanations.append(

                    f"Historical learning found: "
                    f"{cases} similar incident(s), "
                    f"confidence {confidence:.0%}"

                )


        if recommendation:

            if hasattr(
                recommendation,
                "action",
            ):

                action = recommendation.action

            else:

                action = recommendation.get(
                    "action"
                )

            if action:

                explanations.append(
                    f"Recommended action: {action}"
                )


        return {

            "summary":
                explanations[0],


            "explanation":
                explanations,


            "recommendation":
                recommendation or {},


            "confidence":
                (
                    learning.get(
                        "confidence",
                        0
                    )
                    if learning
                    else 0
                ),


            "evidence":
                (
                    learning.get(
                        "evidence",
                        []
                    )
                    if learning
                    else []
                ),


            "generated_at":
                datetime.now(UTC).isoformat(),

        }
