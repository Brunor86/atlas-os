class IntelligenceAnalyzer:


    def analyze(self, history, snapshot=None):

        insights = []


        if not history:
            return insights


        latest = history[-1]


        #
        # System
        #

        if latest["cpu"] > 80:

            insights.append(
                {
                    "type": "warning",
                    "title": "High CPU usage",
                    "message": (
                        f"CPU usage is {latest['cpu']}%"
                    ),
                }
            )


        if latest["memory"] > 85:

            insights.append(
                {
                    "type": "warning",
                    "title": "High memory usage",
                    "message": (
                        f"Memory usage is {latest['memory']}%"
                    ),
                }
            )


        #
        # Docker
        #

        if snapshot:

            docker = snapshot.get(
                "docker",
                {}
            )


            exited = docker.get(
                "exited",
                0
            )


            containers = docker.get(
                "containers",
                []
            )


            stopped_containers = []


            for container in containers:

                status = container.get(
                    "status",
                    ""
                ).lower()


                if status in (
                    "exited",
                    "stopped",
                    "dead",
                ):

                    stopped_containers.append(
                        container
                    )


            if stopped_containers:

                for container in stopped_containers:

                    name = container.get(
                        "name",
                        "unknown"
                    )


                    insights.append(
                        {
                            "type": "warning",
                            "title": "Docker container stopped",
                            "message": (
                                f"{name} container is stopped"
                            ),
                            "asset_id": (
                                f"application-docker-{name}"
                            ),
                            "category": "docker",
                        }
                    )


            elif exited > 0:

                insights.append(
                    {
                        "type": "warning",
                        "title": "Docker containers stopped",
                        "message": (
                            f"{exited} container(s) "
                            "are not running"
                        ),
                    }
                )


        #
        # Storage
        #

        if snapshot:

            disks = snapshot.get(
                "storage",
                []
            )


            for disk in disks:

                usage = disk.get(
                    "usage_percent",
                    0
                )


                if usage > 85:

                    insights.append(
                        {
                            "type": "warning",
                            "title": "Storage capacity",
                            "message": (
                                f"{disk['mountpoint']} "
                                f"is {usage}% full"
                            ),
                        }
                    )


        #
        # Trend memory
        #

        if len(history) >= 3:

            old = history[-3]["memory"]

            current = latest["memory"]


            if current - old > 10:

                insights.append(
                    {
                        "type": "warning",
                        "title": "Memory trend increasing",
                        "message": (
                            "Memory usage increased "
                            "significantly"
                        ),
                    }
                )


        #
        # Health
        #

        if latest["health"] != "healthy":

            insights.append(
                {
                    "type": "warning",
                    "title": "Infrastructure health",
                    "message": (
                        f"Current state: "
                        f"{latest['health']}"
                    ),
                }
            )


        return insights
