class NOCScorer:

    def calculate(self, signals):

        score = 0

        for signal in signals:
            score += signal.get(
                "impact",
                0
            )

        return score


    def priority(self, score):

        if score >= 70:
            return "HIGH"

        if score >= 30:
            return "MEDIUM"

        return "LOW"
