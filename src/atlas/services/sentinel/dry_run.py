from atlas.services.sentinel.live import (
    SentinelLiveService,
)


def main():
    result = (
        SentinelLiveService()
        .dry_run()
    )

    evaluation = (
        result.evaluation
    )

    notifications = {
        item.finding.fingerprint:
            item.reason
        for item
        in evaluation.notifications
    }

    print(
        "========================================"
    )
    print(
        "ATLAS SENTINEL · REAL HOMELAB DRY RUN"
    )
    print(
        "========================================"
    )

    print()
    print(
        "COLLECTED:",
        result.collected_at.isoformat(),
    )

    print()
    print(
        "SOURCES"
    )
    print(
        "-" * 72
    )

    total = 0

    for source in result.sources:
        count = len(
            source.findings
        )

        total += count

        print(
            f"{source.source:20} "
            f"{count} finding(s)"
        )

    print()
    print(
        "FINDINGS"
    )
    print(
        "-" * 72
    )

    if not evaluation.observations:
        print(
            "No active Sentinel findings."
        )

    for finding in (
        evaluation.observations
    ):
        reason = notifications.get(
            finding.fingerprint
        )

        would_notify = (
            reason is not None
        )

        print()
        print(
            f"[{finding.severity.value}] "
            f"{finding.title}"
        )

        print(
            f"Source:  {finding.source}"
        )

        print(
            f"Subject: {finding.subject}"
        )

        print(
            f"Detail:  {finding.summary}"
        )

        print(
            "Would notify:",
            (
                "YES"
                if would_notify
                else "NO"
            ),
        )

        if reason:
            print(
                "Reason:",
                reason,
            )

        print(
            "Fingerprint:",
            finding.fingerprint,
        )

    print()
    print(
        "SUMMARY"
    )
    print(
        "-" * 72
    )

    print(
        "Active findings:",
        total,
    )

    print(
        "Would notify:",
        len(
            evaluation.notifications
        ),
    )

    print(
        "Recoveries:",
        len(
            evaluation.recoveries
        ),
    )

    print()
    print(
        "DRY RUN ONLY · "
        "NO STATE WRITTEN · "
        "NO TELEGRAM SENT"
    )


if __name__ == "__main__":
    main()
