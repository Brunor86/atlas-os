from atlas.storage.repository import SnapshotRepository


class AIAnalyzer:


    def __init__(self):

        self.repository = SnapshotRepository()


    def analyze(self):

        history = self.repository.get_history(20)

        if not history:

            return []


        insights = []


        current = history[-1]


        # ==========================
        # Memory analysis
        # ==========================

        memories = [
            item["memory"]
            for item in history
        ]


        if len(memories) >= 5:

            first = memories[0]
            last = memories[-1]

            increase = last - first


            if increase > 10:

                insights.append(
                    {
                        "type": "warning",
                        "title": "Memory growth detected",
                        "message":
                        f"Memory usage increased {increase:.1f}% over recent snapshots"
                    }
                )


        if current["memory"] > 85:

            insights.append(
                {
                    "type": "critical",
                    "title": "High memory usage",
                    "message":
                    f"Current memory usage is {current['memory']}%"
                }
            )


        # ==========================
        # Docker analysis
        # ==========================

        if current["containers"] < max(
            item["containers"]
            for item in history
        ):

            insights.append(
                {
                    "type": "warning",
                    "title": "Docker containers decreased",
                    "message":
                    "Running containers count decreased compared with previous snapshots"
                }
            )


        # ==========================
        # Storage analysis
        # ==========================

        latest_snapshot = self.repository.get_latest()


        if latest_snapshot:

            data = latest_snapshot["data"]


            for disk in data.get("storage", []):

                usage = disk.get(
                    "usage_percent",
                    0
                )


                if usage > 85:

                    insights.append(
                        {
                            "type": "warning",
                            "title": "Storage warning",
                            "message":
                            f"{disk['mountpoint']} usage is {usage}%"
                        }
                    )


        # ==========================
        # Stability fallback
        # ==========================

        if not insights:

            insights.append(
                {
                    "type": "info",
                    "title": "Infrastructure stable",
                    "message":
                    "No relevant anomalies detected"
                }
            )


        return insights
