from datetime import datetime, UTC


class SeverityIntelligence:


    def analyze(
        self,
        incident
    ):

        reasons = []


        severity = getattr(
            incident,
            "severity",
            "UNKNOWN"
        )


        confidence = getattr(
            incident,
            "confidence",
            0
        )


        impact = getattr(
            incident,
            "impact",
            []
        )


        blast = getattr(
            incident,
            "blast_radius",
            []
        )


        score = 0


        if severity == "CRITICAL":

            score = 100

            reasons.append(
                "critical severity assigned by SeverityEngine"
            )


        elif severity == "HIGH":

            score = 70

            reasons.append(
                "high severity assigned by SeverityEngine"
            )


        elif severity == "MEDIUM":

            score = 40

            reasons.append(
                "medium severity assigned by SeverityEngine"
            )


        elif severity == "LOW":

            score = 10

            reasons.append(
                "low severity assigned by SeverityEngine"
            )



        if confidence >= 0.8:

            reasons.append(
                "high confidence evidence"
            )


        elif confidence >= 0.5:

            reasons.append(
                "medium confidence evidence"
            )



        high_dependencies = [

            item

            for item in impact

            if isinstance(
                item,
                dict
            )

            and item.get(
                "importance"
            ) == "HIGH"

        ]


        if high_dependencies:

            reasons.append(
                "high importance dependency detected"
            )



        if blast:

            reasons.append(
                "blast radius calculated"
            )



        return {

            "severity": severity,

            "score": score,

            "reasons": reasons,

            "timestamp":
                datetime.now(UTC).isoformat(),

        }
