from atlas.core.history import AssetHistory
from datetime import timezone


class HistoryAnalyzer:


    def normalize_datetime(
        self,
        value,
    ):

        if value.tzinfo is None:

            return value.replace(
                tzinfo=timezone.utc
            )


        return value



    def analyze(
        self,
        history: list[AssetHistory],
    ):

        if not history:

            return {
                "trend": "unknown",
                "delta": 0,
                "message": "No historical data available",
            }



        if len(history) == 1:

            return {

                "trend": "initializing",

                "delta": 0,

                "message":
                    "First observation collected, waiting for historical trend",

                "samples": 1,

                "first_health":
                    history[0].health,

                "last_health":
                    history[0].health,

            }



        for item in history:

            item.snapshot_at = self.normalize_datetime(
                item.snapshot_at
            )



        ordered = sorted(
            history,
            key=lambda x: x.snapshot_at,
        )



        first = ordered[0]

        last = ordered[-1]



        delta = last.health - first.health



        duration = (
            last.snapshot_at -
            first.snapshot_at
        )


        duration_hours = round(
            duration.total_seconds() / 3600,
            2,
        )


        duration_days = round(
            duration_hours / 24,
            2,
        )


        rate_per_day = 0


        if duration_days > 0:

            rate_per_day = round(
                delta / duration_days,
                2,
            )



        velocity = "stable"


        if rate_per_day <= -10:

            velocity = "fast"


        elif rate_per_day <= -5:

            velocity = "moderate"


        elif rate_per_day < 0:

            velocity = "slow"



        trend = "stable"

        message = "Asset health is stable"



        if delta <= -20:

            trend = "degrading"

            message = (
                "Asset health is decreasing significantly"
            )


        elif delta < 0:

            trend = "declining"

            message = (
                "Asset health is slowly decreasing"
            )


        elif delta >= 20:

            trend = "improving"

            message = (
                "Asset health is improving"
            )



        return {

            "trend": trend,

            "delta": delta,

            "message": message,

            "samples": len(history),

            "first_health": first.health,

            "last_health": last.health,

            "duration_hours": duration_hours,

            "duration_days": duration_days,

            "rate_per_day": rate_per_day,

            "velocity": velocity,

        }
