class AIReasoningEngine:


    def analyze(
        self,
        context,
    ):


        incidents = context.get(
            "incidents",
            []
        )


        recommendations = context.get(
            "recommendations",
            []
        )


        logs = context.get(
            "logs",
            []
        )


        health = context.get(
            "health",
            {}
        )


        findings = health.get(
            "findings",
            []
        )


        intelligence = context.get(
            "intelligence",
            {}
        )


        correlated_issues = intelligence.get(
            "issues",
            []
        )


        reasoning = []

        actions = []

        score = 0



        #
        # Health findings intelligence
        #

        for finding in findings:


            severity = finding.get(
                "severity",
                "WARNING",
            ).upper()


            occurrences = finding.get(
                "occurrences",
                1,
            )


            if severity == "CRITICAL":

                score += 60


            elif severity == "WARNING":

                score += 30


            else:

                score += 10



            if occurrences >= 3:

                score += 10



            asset_id = finding.get(
                "asset_id",
                "unknown",
            )


            title = finding.get(
                "title",
                "unknown finding",
            )



            reasoning.append(

                f"{asset_id} reports {title} "
                f"({occurrences} occurrences)"

            )



            #
            # Operational actions
            #

            if "SMART" in title.upper():

                actions.append(

                    f"Investigate {asset_id} SMART failure"

                )

            else:

                actions.append(

                    f"Investigate {title} on {asset_id}"

                )



        #
        # Correlated intelligence
        #

        for issue in correlated_issues:


            asset_id = issue.asset_id


            category = issue.category


            confidence = issue.confidence


            score += int(
                50 * confidence
            )


            reasoning.append(

                f"{asset_id} correlated issue detected: "
                f"{category} "
                f"(confidence {confidence})"

            )


            reasoning.append(

                issue.explanation

            )


            if issue.signals:


                reasoning.append(

                    "Signals: "
                    +
                    ", ".join(
                        issue.signals
                    )

                )



            if category == "storage_degradation":


                actions.append(

                    "Check disk health and physical connectivity"

                )



        #
        # Historical intelligence
        #

        assets_context = context.get(
            "assets",
            {}
        )


        inventory = assets_context.get(
            "inventory",
            []
        )



        for asset in inventory:


            history = asset.get(
                "history",
                {}
            )


            trend = history.get(
                "trend",
                "unknown"
            )


            delta = history.get(
                "delta",
                0
            )


            velocity = history.get(
                "velocity"
            )


            asset_id = asset.get(
                "id",
                "unknown"
            )



            if trend == "degrading":


                score += 30


                reasoning.append(

                    f"{asset_id} health degraded historically "
                    f"(delta {delta})"

                )


                actions.append(

                    "Review storage degradation trend"

                )



            elif trend == "declining":


                score += 15


                reasoning.append(

                    f"{asset_id} shows slow health decline "
                    f"(delta {delta})"

                )



            if velocity == "fast":


                score += 20


                reasoning.append(

                    f"{asset_id} degradation velocity is fast "
                    f"({history.get('rate_per_day')} health/day)"

                )


                actions.append(

                    "Check disk health and physical connectivity"

                )



        #
        # Incident analysis
        #

        for incident in incidents:


            name = incident.get(
                "name",
                ""
            )


            if name == "resource_pressure":


                score += 60


                reasoning.append(

                    "Resource consumption may affect stability"

                )



            elif name == "storage_risk":


                score += 70


                reasoning.append(

                    "Storage capacity risk detected"

                )



            elif name == "infrastructure_degradation":


                score += 30


                reasoning.append(

                    "Operational service degradation detected"

                )



        #
        # Log intelligence
        #

        for item in logs:


            container = item.get(
                "container",
                "unknown"
            )


            analysis = item.get(
                "analysis",
                {}
            )


            severity = analysis.get(
                "severity",
                "UNKNOWN"
            )


            confidence = analysis.get(
                "confidence",
                0
            )


            pattern = analysis.get(
                "pattern"
            )


            count = analysis.get(
                "count",
                0
            )



            if pattern == "repeated_exception":


                score += int(
                    60 * confidence
                )


                reasoning.append(

                    f"{container} shows repeated exceptions "
                    f"({count}) with confidence {confidence}"

                )


                actions.append(

                    f"Inspect recurring exceptions in {container}"

                )



            elif pattern in (
                "fatal",
                "database_error",
            ):


                score += int(
                    80 * confidence
                )


                reasoning.append(

                    f"{container} reports critical failures"

                )


                actions.append(

                    f"Inspect critical errors in {container}"

                )



            elif severity == "HIGH":


                score += int(
                    50 * confidence
                )


                reasoning.append(

                    f"{container} shows {pattern} "
                    f"with confidence {confidence}"

                )


                actions.append(

                    f"Inspect logs of {container}"

                )



            elif severity == "MEDIUM":


                score += 15


                reasoning.append(

                    f"{container} generated warning pattern {pattern}"

                )



            elif pattern == "graceful_stop":


                reasoning.append(

                    f"{container} stopped gracefully"

                )


                actions.append(

                    f"Verify availability of {container}"

                )



        #
        # Recommendations
        #

        for recommendation in recommendations:


            actions.extend(

                recommendation.get(
                    "actions",
                    []
                )

            )



        #
        # Priority calculation
        #

        if score >= 80:


            priority = "CRITICAL"


            summary = (
                "Infrastructure has critical conditions "
                "requiring immediate intervention."
            )



        elif score >= 50:


            priority = "HIGH"


            summary = (
                "Infrastructure requires immediate attention."
            )



        elif score >= 20:


            priority = "MEDIUM"


            summary = (
                "Infrastructure requires monitoring."
            )



        else:


            priority = "LOW"


            summary = (
                "Infrastructure is operating normally."
            )



        #
        # Confidence
        #

        if score == 0:

            confidence = 0.9


        else:

            confidence = min(
                0.95,
                round(
                    0.5 +
                    (score / 200),
                    2
                )
            )



        if not reasoning:


            reasoning.append(

                "No relevant operational issues detected"

            )



        #
        # Remove duplicate actions
        #

        actions = list(
            dict.fromkeys(
                actions
            )
        )



        return {


            "priority":

                priority,


            "summary":

                summary,


            "confidence":

                confidence,


            "score":

                score,


            "reasoning":

                reasoning,


            "actions":

                actions[:10],

        }
