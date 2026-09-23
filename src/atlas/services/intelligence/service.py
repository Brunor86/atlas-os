from atlas.services.intelligence.correlation import (
    CorrelatedIssue,
)



class IntelligenceService:


    def analyze(
        self,
        context,
    ):

        issues = []


        assets = (
            context
            .get("assets", {})
            .get("inventory", [])
        )



        findings = (
            context
            .get("health", {})
            .get("findings", [])
        )



        findings_by_asset = {}


        for finding in findings:

            asset_id = finding.get(
                "asset_id"
            )


            findings_by_asset.setdefault(
                asset_id,
                []
            ).append(
                finding
            )



        for asset in assets:


            asset_id = asset.get(
                "id"
            )


            signals = []


            history = asset.get(
                "history",
                {}
            )


            trend = history.get(
                "trend"
            )


            velocity = history.get(
                "velocity"
            )



            if trend == "degrading":

                signals.append(
                    "historical degradation"
                )



            if velocity == "fast":

                signals.append(
                    "fast health decline"
                )



            for finding in findings_by_asset.get(
                asset_id,
                []
            ):


                title = finding.get(
                    "title",
                    ""
                )


                message = finding.get(
                    "message",
                    ""
                )


                combined = (
                    title + " " + message
                ).upper()


                if (
                    "SMART" in combined
                    and
                    "UNAVAILABLE" not in combined
                ):

                    signals.append(
                        "SMART failure detected"
                    )



            if len(signals) >= 2:


                issues.append(

                    CorrelatedIssue(

                        asset_id=asset_id,

                        category="storage_degradation",

                        severity="HIGH",

                        confidence=0.85,

                        signals=signals,

                        explanation=(

                            "Multiple storage health signals "
                            "indicate possible degradation"

                        ),

                    )

                )



        return issues
