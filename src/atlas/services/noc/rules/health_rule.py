class HealthRule:


    def evaluate(
        self,
        health,
    ):

        signals = []


        if not health:

            return signals



        #
        # Existing health status
        #

        if getattr(
            health,
            "status",
            "healthy",
        ) != "healthy":


            signals.append(
                {
                    "source": "health",
                    "impact": 30,
                    "severity": "warning",
                    "message":
                        (
                            f"Health status degraded: "
                            f"{health.status}"
                        ),
                }
            )



        #
        # Existing alerts
        #

        alerts = getattr(
            health,
            "alerts",
            []
        )


        if alerts:

            highest = "warning"

            for alert in alerts:

                severity = getattr(
                    alert,
                    "severity",
                    "warning",
                ).lower()

                if severity == "critical":
                    highest = "critical"


            signals.append(
                {
                    "source": "health",
                    "impact": (
                        60
                        if highest == "critical"
                        else 35
                    ),
                    "severity": highest,
                    "message":
                        (
                            f"{len(alerts)} active alerts"
                        ),
                }
            )



        #
        # Health findings
        #

        findings = getattr(
            health,
            "findings",
            []
        )


        for finding in findings:


            severity = finding.get(
                "severity",
                "warning",
            ).lower()



            impact = 20


            if severity == "critical":

                impact = 60


            elif severity == "warning":

                impact = 35



            occurrences = finding.get(
                "occurrences",
                1,
            )



            if occurrences >= 3:

                impact += 10



            signals.append(
                {
                    "source":
                        "health_finding",

                    "impact":
                        impact,

                    "severity":
                        severity,

                    "message":
                        (
                            f"{finding.get('title')} "
                            f"for "
                            f"{finding.get('asset_id')}: "
                            f"{finding.get('message')} "
                            f"(occurrences="
                            f"{occurrences})"
                        ),

                    "asset_id":
                        finding.get(
                            "asset_id"
                        ),

                }
            )



        return signals
