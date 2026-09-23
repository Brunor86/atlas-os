from atlas.core.asset import Criticality


DOCKER_CRITICALITY_LABEL = (
    "atlas.criticality"
)


def parse_criticality(
    value,
    default=Criticality.MEDIUM,
):
    """
    Convert declarative metadata into the canonical Criticality enum.

    Invalid or missing values deliberately fall back to the supplied
    neutral default instead of guessing based on application identity.
    """

    if isinstance(
        value,
        Criticality,
    ):
        return value

    if value is None:
        return default

    normalized = str(
        value
    ).strip().upper()

    if not normalized:
        return default

    try:
        return Criticality[
            normalized
        ]
    except KeyError:
        return default


def criticality_from_labels(
    labels,
    default=Criticality.MEDIUM,
):
    """
    Resolve asset criticality from Docker/runtime labels.
    """

    if not isinstance(
        labels,
        dict,
    ):
        return default

    return parse_criticality(
        labels.get(
            DOCKER_CRITICALITY_LABEL
        ),
        default=default,
    )
