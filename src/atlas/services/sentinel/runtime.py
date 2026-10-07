from dataclasses import dataclass

from atlas.services.sentinel.live import (
    SentinelLiveService,
)


@dataclass(
    frozen=True,
    slots=True,
)
class SentinelRunResult:
    live_result: object
    delivered: tuple
    state_saved: bool


class SentinelRuntime:
    """
    Delivery coordinator.

    Important reliability rule:

    Sentinel state advances only after every notification
    that should be delivered has been sent successfully.

    Therefore a Telegram failure causes the notification
    to be retried in a later cycle rather than silently
    deduplicated away.
    """

    def __init__(
        self,
        *,
        live_service=None,
        state_store,
        notifier=None,
    ):
        self.live_service = (
            live_service
            or SentinelLiveService()
        )

        self.state_store = (
            state_store
        )

        self.notifier = notifier

    def run(
        self,
        *,
        dry_run=True,
    ):
        previous = (
            self.state_store.load()
        )

        live_result = (
            self.live_service.dry_run(
                previous_state=previous
            )
        )

        evaluation = (
            live_result.evaluation
        )

        if dry_run:
            return SentinelRunResult(
                live_result=live_result,
                delivered=(),
                state_saved=False,
            )

        if self.notifier is None:
            raise RuntimeError(
                "Sentinel live mode "
                "requires a notifier"
            )

        delivered = []

        #
        # Do not persist state before delivery succeeds.
        #
        for notification in (
            evaluation.notifications
        ):
            result = self.notifier.send(
                notification
            )

            delivered.append(
                result
            )

        self.state_store.save(
            evaluation.next_state
        )

        return SentinelRunResult(
            live_result=live_result,
            delivered=tuple(
                delivered
            ),
            state_saved=True,
        )
