from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

from atlas.services.sentinel.contracts import (
    SentinelFinding,
    SentinelNotification,
    SentinelState,
)
from atlas.services.sentinel.policy import (
    SentinelNotificationPolicy,
)


@dataclass(
    frozen=True,
    slots=True,
)
class SentinelEvaluation:
    observations: tuple[SentinelFinding, ...]
    recoveries: tuple[SentinelFinding, ...]
    notifications: tuple[
        SentinelNotification,
        ...
    ]

    next_state: Mapping[
        str,
        SentinelFinding,
    ]


class SentinelEngine:
    """
    Reconcile one Sentinel observation cycle against
    the previously persisted Sentinel state.

    The engine performs no I/O. It does not discover
    infrastructure, write SQLite, send notifications or
    execute actions.
    """

    def __init__(
        self,
        *,
        policy=None,
    ):
        self.policy = (
            policy
            or SentinelNotificationPolicy()
        )

    def evaluate(
        self,
        observations: Sequence[
            SentinelFinding
        ],
        previous_state: Mapping[
            str,
            SentinelFinding
        ],
        *,
        observed_at: datetime,
    ) -> SentinelEvaluation:

        current = {}

        for finding in observations:
            if (
                finding.state
                != SentinelState.OPEN
            ):
                raise ValueError(
                    "Sentinel observations must "
                    "represent OPEN conditions"
                )

            if finding.fingerprint in current:
                raise ValueError(
                    "duplicate Sentinel fingerprint: "
                    f"{finding.fingerprint}"
                )

            current[
                finding.fingerprint
            ] = finding

        notifications = []
        recoveries = []
        next_state = {}

        for fingerprint, finding in (
            current.items()
        ):
            previous = previous_state.get(
                fingerprint
            )

            decision = self.policy.decide(
                finding,
                previous,
            )

            if decision.notify:
                notifications.append(
                    SentinelNotification(
                        finding=finding,
                        reason=decision.reason,
                    )
                )

            next_state[
                fingerprint
            ] = finding

        for fingerprint, previous in (
            previous_state.items()
        ):
            if fingerprint in current:
                continue

            if (
                previous.state
                == SentinelState.RECOVERED
            ):
                next_state[
                    fingerprint
                ] = previous

                continue

            recovered = previous.recovered(
                observed_at=observed_at
            )

            recoveries.append(
                recovered
            )

            decision = self.policy.decide(
                recovered,
                previous,
            )

            if decision.notify:
                notifications.append(
                    SentinelNotification(
                        finding=recovered,
                        reason=decision.reason,
                    )
                )

            next_state[
                fingerprint
            ] = recovered

        return SentinelEvaluation(
            observations=tuple(
                current.values()
            ),
            recoveries=tuple(
                recoveries
            ),
            notifications=tuple(
                notifications
            ),
            next_state=next_state,
        )
