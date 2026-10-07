from dataclasses import dataclass

from atlas.services.sentinel.contracts import (
    SEVERITY_RANK,
    SentinelFinding,
    SentinelSeverity,
    SentinelState,
)


@dataclass(
    frozen=True,
    slots=True,
)
class SentinelDecision:
    notify: bool
    reason: str


class SentinelNotificationPolicy:
    """
    Conservative Sentinel v0.1 notification policy.

    INFO:
        Record state but do not notify.

    WARNING:
        Notify when new, reopened or escalated.

    CRITICAL:
        Notify when new, reopened or escalated.

    RECOVERED:
        Notify once when a previously actionable
        condition returns to normal.
    """

    actionable_rank = SEVERITY_RANK[
        SentinelSeverity.WARNING
    ]

    def decide(
        self,
        current: SentinelFinding,
        previous: SentinelFinding | None,
    ) -> SentinelDecision:

        if (
            current.state
            == SentinelState.RECOVERED
        ):
            if (
                previous is not None
                and previous.state
                == SentinelState.OPEN
                and SEVERITY_RANK[
                    previous.severity
                ]
                >= self.actionable_rank
            ):
                return SentinelDecision(
                    notify=True,
                    reason="recovered",
                )

            return SentinelDecision(
                notify=False,
                reason="recovery_not_actionable",
            )

        current_actionable = (
            SEVERITY_RANK[
                current.severity
            ]
            >= self.actionable_rank
        )

        if previous is None:
            if current_actionable:
                return SentinelDecision(
                    notify=True,
                    reason=(
                        "new_"
                        f"{current.severity.value.lower()}"
                    ),
                )

            return SentinelDecision(
                notify=False,
                reason="new_info",
            )

        if (
            previous.state
            == SentinelState.RECOVERED
        ):
            if current_actionable:
                return SentinelDecision(
                    notify=True,
                    reason="reopened",
                )

            return SentinelDecision(
                notify=False,
                reason="reopened_info",
            )

        if (
            SEVERITY_RANK[
                current.severity
            ]
            >
            SEVERITY_RANK[
                previous.severity
            ]
            and current_actionable
        ):
            return SentinelDecision(
                notify=True,
                reason="severity_escalated",
            )

        return SentinelDecision(
            notify=False,
            reason="unchanged",
        )
