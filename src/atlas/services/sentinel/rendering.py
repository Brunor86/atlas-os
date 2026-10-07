from atlas.services.sentinel.contracts import (
    SentinelState,
)


class SentinelMessageRenderer:
    @staticmethod
    def render(
        notification,
    ):
        finding = (
            notification.finding
        )

        if (
            finding.state
            == SentinelState.RECOVERED
        ):
            icon = "✅"
            status = "RECOVERED"
        elif (
            finding.severity.value
            == "CRITICAL"
        ):
            icon = "🚨"
            status = "CRITICAL"
        elif (
            finding.severity.value
            == "WARNING"
        ):
            icon = "⚠️"
            status = "WARNING"
        else:
            icon = "ℹ️"
            status = "INFO"

        lines = [
            f"{icon} ATLAS SENTINEL · {status}",
            "",
            finding.title,
            finding.summary,
            "",
            f"Source: {finding.source}",
            f"Subject: {finding.subject}",
        ]

        return "\n".join(
            lines
        )
