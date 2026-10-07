import hashlib
import re


def _normalize(
    value,
):
    text = str(
        value or ""
    )

    text = text.strip().lower()

    return re.sub(
        r"\s+",
        " ",
        text,
    )


def sentinel_fingerprint(
    *,
    source,
    kind,
    subject,
):
    """
    Stable identity for one operational condition.

    Human-readable text such as title or summary is
    intentionally excluded so wording changes do not
    generate duplicate Sentinel findings.
    """

    identity = "|".join(
        (
            _normalize(source),
            _normalize(kind),
            _normalize(subject),
        )
    )

    digest = hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()

    return (
        "sentinel:v1:"
        f"{digest[:24]}"
    )
