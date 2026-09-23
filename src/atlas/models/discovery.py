from dataclasses import dataclass, field

from atlas.core.asset import Asset


@dataclass
class DiscoveryResult:

    assets: list[Asset] = field(
        default_factory=list
    )

    providers: list[str] = field(
        default_factory=list
    )

    count: int = 0

    #
    # A discovery is authoritative only when every asset source
    # required by the cycle completed successfully.
    #
    # Partial discovery must never be interpreted as proof that
    # previously known assets disappeared.
    #
    complete: bool = True

    errors: list[str] = field(
        default_factory=list
    )
