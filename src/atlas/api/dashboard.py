def health_score_from_noc_score(
    noc_score: int,
) -> int:
    """
    Convert the internal NOC impact score into a
    user-facing health score.

    Internal NOC semantics:
        0   = no detected impact
        30+ = warning
        70+ = critical

    Dashboard semantics:
        100 = fully healthy
        0   = maximum displayed degradation

    The internal NOC score remains authoritative and
    unchanged. This function is presentation-only.
    """

    score = max(
        0,
        int(
            noc_score
            or 0
        ),
    )

    return max(
        0,
        100 - score,
    )
