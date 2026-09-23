from datetime import datetime, UTC


class IncidentMemoryIntelligence:


    def __init__(
        self,
        repository=None,
    ):

        self.repository = repository



    def analyze(
        self,
        incident,
    ):

        if not self.repository:

            return {

                "similar_cases": 0,

                "successful_actions": [],

                "success_rate": 0,

                "confidence": 0,

                "generated_at":
                    datetime.now(UTC).isoformat(),

            }



        history = self.repository.get_similar_incidents(

            incident.asset,

            incident.root_cause,

        )


        if not history:

            return {

                "similar_cases": 0,

                "successful_actions": [],

                "success_rate": 0,

                "confidence": 0,

                "generated_at":
                    datetime.now(UTC).isoformat(),

            }



        actions = []


        for item in history:

            if len(item) > 9:

                raw_actions = item[9]

                if raw_actions:

                    try:

                        parsed = eval(
                            raw_actions
                        )

                        if isinstance(
                            parsed,
                            list
                        ):

                            actions.extend(
                                parsed
                            )

                    except Exception:

                        pass



        #
        # fallback: learn from successful historical executions
        #

        if not actions:

            historical_actions = (
                self.repository.get_successful_learning_actions()
            )


            for row in historical_actions:

                if row[0]:

                    actions.append(
                        row[0]
                    )


        learning = self.repository.get_learning_records()


        successful = []


        for row in learning:

            if row[2] in actions and row[3] == "SUCCESS":

                successful.append(
                    row[2]
                )



        success_rate = 0


        if actions:

            success_rate = (
                len(successful)
                /
                len(actions)
            )



        confidence = min(

            1.0,

            (
                len(history)
                *
                0.2
            )
            +
            (
                success_rate
                *
                0.5
            )

        )



        return {

            "similar_cases":
                len(history),

            "successful_actions":
                list(
                    set(successful)
                ),

            "success_rate":
                success_rate,

            "confidence":
                confidence,

            "generated_at":
                datetime.now(UTC).isoformat(),

        }


    def get_successful_actions(
        self,
    ):

        if not self.repository:

            return []


        records = self.repository.get_learning_records()


        actions = []


        for row in records:

            if row[3] == "SUCCESS":

                actions.append(
                    row[2]
                )


        return list(
            set(actions)
        )
