import argparse
import os

from atlas.services.sentinel.rendering import (
    SentinelMessageRenderer,
)
from atlas.services.sentinel.runtime import (
    SentinelRuntime,
)
from atlas.services.sentinel.state import (
    SentinelStateStore,
)
from atlas.services.sentinel.telegram import (
    TelegramNotifier,
)


DEFAULT_STATE_PATH = (
    "/var/lib/atlas/sentinel/"
    "state.json"
)


def _print_result(
    result,
    *,
    dry_run,
):
    evaluation = (
        result.live_result.evaluation
    )

    reasons = {
        notification.finding.fingerprint:
            notification
        for notification
        in evaluation.notifications
    }

    print(
        "========================================"
    )

    print(
        "ATLAS SENTINEL · "
        + (
            "DRY RUN"
            if dry_run
            else "LIVE RUN"
        )
    )

    print(
        "========================================"
    )

    print()

    if not evaluation.observations:
        print(
            "No active Sentinel findings."
        )

    renderer = (
        SentinelMessageRenderer()
    )

    for finding in (
        evaluation.observations
    ):
        notification = (
            reasons.get(
                finding.fingerprint
            )
        )

        print(
            f"[{finding.severity.value}] "
            f"{finding.title}"
        )

        print(
            finding.summary
        )

        print(
            "Notify:",
            (
                "YES"
                if notification
                else "NO"
            ),
        )

        if notification:
            print()
            print(
                "--- Telegram preview ---"
            )
            print(
                renderer.render(
                    notification
                )
            )
            print(
                "------------------------"
            )

        print()

    for recovered in (
        evaluation.recoveries
    ):
        notification = (
            reasons.get(
                recovered.fingerprint
            )
        )

        print(
            "[RECOVERED]",
            recovered.title,
        )

        print(
            recovered.summary
        )

        print(
            "Notify:",
            (
                "YES"
                if notification
                else "NO"
            ),
        )

        if notification:
            print()
            print(
                "--- Telegram preview ---"
            )

            print(
                renderer.render(
                    notification
                )
            )

            print(
                "------------------------"
            )

        print()

    print(
        "Notifications:",
        len(
            evaluation.notifications
        ),
    )

    print(
        "Delivered:",
        len(
            result.delivered
        ),
    )

    print(
        "State saved:",
        (
            "YES"
            if result.state_saved
            else "NO"
        ),
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "ATLAS Sentinel operational runner"
        )
    )

    mode = (
        parser.add_mutually_exclusive_group()
    )

    mode.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Evaluate and render notifications "
            "without sending or saving state."
        ),
    )

    mode.add_argument(
        "--live",
        action="store_true",
        help=(
            "Send notifications and persist "
            "deduplication state."
        ),
    )

    parser.add_argument(
        "--state-path",
        default=(
            os.environ.get(
                "ATLAS_SENTINEL_STATE_PATH"
            )
            or DEFAULT_STATE_PATH
        ),
    )

    parser.add_argument(
        "--telegram-probe",
        action="store_true",
        help=(
            "Validate Telegram bot credentials "
            "without sending a message."
        ),
    )

    args = parser.parse_args()

    #
    # Default is deliberately safe.
    #
    dry_run = not args.live

    if args.telegram_probe:
        notifier = (
            TelegramNotifier()
        )

        result = (
            notifier.probe()
        )

        print(
            "TELEGRAM BOT: VERIFIED"
        )

        print(
            "USERNAME:",
            result.get(
                "username"
            ),
        )

        print(
            "NAME:",
            result.get(
                "name"
            ),
        )

        return

    notifier = (
        TelegramNotifier()
        if args.live
        else None
    )

    runtime = SentinelRuntime(
        state_store=(
            SentinelStateStore(
                args.state_path
            )
        ),
        notifier=notifier,
    )

    result = runtime.run(
        dry_run=dry_run
    )

    _print_result(
        result,
        dry_run=dry_run,
    )


if __name__ == "__main__":
    main()
