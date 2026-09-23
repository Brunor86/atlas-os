class AIRecommender:


    def analyze(
        self,
        incidents,
    ):

        recommendations = []


        for incident in incidents:


            name = incident.get(
                "name",
                ""
            )


            if name == "infrastructure_degradation":

                recommendations.append(

                    {
                        "incident":
                            name,

                        "diagnosis":
                            "Infrastructure degradation caused by operational service issues.",

                        "probable_causes":
                            [
                                "Docker container stopped unexpectedly",
                                "Application failure",
                                "Manual service interruption",
                            ],

                        "impact":
                            "One or more infrastructure services may be unavailable.",

                        "actions":
                            [
                                "Check stopped containers",
                                "Inspect container logs",
                                "Restart affected services if required",
                            ],

                    }

                )



            elif name == "resource_pressure":

                recommendations.append(

                    {
                        "incident":
                            name,

                        "diagnosis":
                            "Resource consumption is affecting infrastructure stability.",

                        "probable_causes":
                            [
                                "High memory consumption",
                                "Container resource leak",
                                "Heavy workload",
                            ],

                        "impact":
                            "Possible performance degradation.",

                        "actions":
                            [
                                "Check memory usage",
                                "Review container consumption",
                                "Analyze historical trends",
                            ],
                    }

                )



            elif name == "storage_risk":

                recommendations.append(

                    {
                        "incident":
                            name,

                        "diagnosis":
                            "Storage capacity risk detected.",

                        "probable_causes":
                            [
                                "Disk usage growth",
                                "Large files accumulation",
                            ],

                        "impact":
                            "Future service failures due to lack of space.",

                        "actions":
                            [
                                "Review disk usage",
                                "Remove unnecessary data",
                                "Increase storage capacity",
                            ],

                    }

                )


        return recommendations

