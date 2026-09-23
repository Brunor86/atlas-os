class IntelligenceMemoryService:


    def __init__(
        self,
        repository=None,
    ):

        self.repository = repository



    def lookup(
        self,
        asset,
        issue,
    ):

        matches = []


        if not self.repository:

            return {

                "matches": 0,

                "evidence": [],

                "confidence": 0,

            }



        queries = [

            issue,

            "container stopped",

            "container failure",

            "docker",

        ]



        history = []


        for query in queries:

            result = self.repository.get_similar_incidents(

                asset,

                query,

            )

            history.extend(result)



        seen = set()


        for item in history:

            key = str(item)


            if key in seen:

                continue


            seen.add(key)


            matches.append(

                {

                    "incident": item

                }

            )



        confidence = 0


        if matches:

            confidence = min(

                len(matches) * 0.2,

                1.0,

            )



        return {

            "matches": len(matches),

            "evidence": matches,

            "confidence": confidence,

        }
