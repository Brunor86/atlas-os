
from atlas.core.finding import HealthFinding


class AISeverityEngine:


    SEVERITY_SCORE = {

        "CRITICAL": 40,

        "HIGH": 25,

        "MEDIUM": 15,

        "LOW": 5,

    }


    def score(
        self,
        findings: list[HealthFinding],
    ):

        total = 0

        details = []


        for finding in findings:

            severity = finding.severity.upper()

            points = self.SEVERITY_SCORE.get(
                severity,
                0,
            )


            if finding.occurrences > 1:

                points += min(
                    finding.occurrences * 2,
                    20,
                )


            total += points


            details.append(

                {
                    "asset": finding.asset_id,

                    "severity":
                        severity,

                    "title":
                        finding.title,

                    "points":
                        points,

                }

            )


        return {

            "risk":
                min(total,100),

            "details":
                details,

        }
