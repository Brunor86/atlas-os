from dataclasses import dataclass, field


@dataclass(slots=True)
class Alert:

    severity: str

    source: str

    title: str

    message: str

    affected_assets: list[str] = field(
        default_factory=list
    )
