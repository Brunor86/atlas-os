from atlas.core.asset import (
    Criticality,
)

from atlas.services.assets.criticality import (
    criticality_from_labels,
    parse_criticality,
)


def test_missing_criticality_is_medium():

    assert (
        criticality_from_labels(
            {}
        )
        == Criticality.MEDIUM
    )


def test_declared_criticality_is_resolved():

    assert (
        criticality_from_labels(
            {
                "atlas.criticality":
                    "CRITICAL",
            }
        )
        == Criticality.CRITICAL
    )


def test_declared_high_criticality_is_resolved():

    assert (
        criticality_from_labels(
            {
                "atlas.criticality":
                    "high",
            }
        )
        == Criticality.HIGH
    )


def test_invalid_criticality_does_not_guess():

    assert (
        parse_criticality(
            "important-super-app"
        )
        == Criticality.MEDIUM
    )
