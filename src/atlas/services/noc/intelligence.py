class NOCIntelligence:


    def analyze(
        self,
        issues,
        incidents,
    ):


        explanations = []

        recommendations = []



        for incident in incidents:


            if incident.name == "infrastructure_degradation":


                explanations.append(

                    "Infrastructure degradation detected."

                )


                recommendations.append(

                    "Review infrastructure services and container status."

                )



            elif incident.name == "resource_pressure":


                explanations.append(

                    "Resource pressure detected."

                )


                recommendations.append(

                    "Review memory and CPU consumption."

                )



            elif incident.name == "storage_risk":


                explanations.append(

                    "Storage risk detected."

                )


                recommendations.append(

                    "Check disk usage and filesystem health."

                )



            elif incident.name == "service_degradation":


                evidence = []


                for event in incident.events:


                    if isinstance(
                        event,
                        dict
                    ):


                        detail = event.get(

                            "detail",

                            ""

                        )


                        if detail:

                            evidence.append(
                                detail
                            )



                if evidence:


                    explanations.append(

                        "Service degradation detected caused by: "
                        +
                        "; ".join(
                            evidence
                        )

                    )

                else:


                    explanations.append(

                        "Service degradation detected from correlated events and logs."

                    )



                recommendations.append(

                    "Inspect affected container logs and restart service if required."

                )


                #
                # Dependency impact analysis
                #

                impact = getattr(
                    incident,
                    "impact",
                    []
                )


                if impact:


                    affected = []


                    high_impact = []


                    details = []


                    for item in impact:


                        if isinstance(
                            item,
                            dict
                        ):


                            application = item.get(
                                "application"
                            )


                            if application:


                                affected.append(
                                    application
                                )


                            if item.get(
                                "importance"
                            ) == "HIGH":


                                high_impact.append(
                                    application
                                )


                            details.append(

                                f"{application}: "
                                f"role={item.get('roles')}, "
                                f"reason={item.get('reason')}"

                            )


                    if affected:


                        explanations.append(

                            "Dependency impact detected: "
                            +
                            ", ".join(
                                affected
                            )

                        )


                    if details:


                        explanations.append(

                            "Impact details: "
                            +
                            " | ".join(
                                details
                            )

                        )


                    if high_impact:


                        recommendations.append(

                            "Restore root dependency first. "
                            "High impact services: "
                            +
                            ", ".join(
                                high_impact
                            )

                        )



        return {


            "explanations":

                explanations,


            "recommendations":

                recommendations,


        }
