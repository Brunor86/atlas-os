from datetime import datetime, UTC


class LearningContextService:


    def __init__(
        self,
        repository=None,
    ):

        self.repository = repository



    def get_context(
        self,
        incident,
    ):

        if not self.repository:

            return {

                "similar_cases": 0,

                "success_rate": 0,

                "confidence": 0,

                "evidence": [],

                "generated_at": datetime.now(UTC).isoformat(),

            }



        rows = self.repository.get_learning_records()



        if not rows:

            return {

                "similar_cases": 0,

                "success_rate": 0,

                "confidence": 0,

                "evidence": [],

                "generated_at": datetime.now(UTC).isoformat(),

            }



        matches = []


        context = (

            incident.name

            +

            " "

            +

            incident.reason

        ).lower()



        for row in rows:

            action = row[2]

            result = row[3]

            resolution = row[4]



            text = (

                str(action)

                +

                " "

                +

                str(resolution)

            ).lower()



            if any(
                word in text
                for word in context.split()
                if len(word) > 4
            ):

                matches.append(row)



        if not matches:

            return {

                "similar_cases": 0,

                "success_rate": 0,

                "confidence": 0,

                "evidence": [],

                "generated_at": datetime.now(UTC).isoformat(),

            }



        successes = [

            row

            for row in matches

            if row[3] == "SUCCESS"

        ]



        evidence = []


        actions = []


        for row in successes:

            actions.append(
                row[2]
            )


            if len(row) > 7 and row[7]:

                item = row[7]

                if isinstance(item, list):
                    item = " | ".join(
                        str(x)
                        for x in item
                    )

                if item not in evidence:
                    evidence.append(
                        item
                    )


        recommended_action = None


        if actions:

            recommended_action = max(
                set(actions),
                key=actions.count
            )



        return {

            "similar_cases": len(matches),

            "success_rate":

                len(successes)
                /
                len(matches),


            "confidence":

                min(
                    1.0,
                    0.5
                    +
                    (
                        len(successes)
                        /
                        len(matches)
                    )
                    *
                    0.5
                ),


            "recommended_action": recommended_action,


            "evidence": evidence,


            "generated_at":
                datetime.now(UTC).isoformat(),

        }
