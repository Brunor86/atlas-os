from dataclasses import dataclass


@dataclass(slots=True)
class Insight:

    title: str

    summary: str

    severity: str

    asset_id: str | None = None
