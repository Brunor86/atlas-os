
class AIPolicyEngine:


    def select_purpose(
        self,
        context,
    ):


        risk = context.get(
            "risk",
            0,
        )


        severity = context.get(
            "severity",
            "",
        )


        if severity == "CRITICAL":

            return "reasoning"


        if risk >= 70:

            return "reasoning"


        return "summary"
