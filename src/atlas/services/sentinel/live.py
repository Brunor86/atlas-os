from dataclasses import dataclass
from datetime import (
    UTC,
    datetime,
)

from atlas.services.sentinel.engine import (
    SentinelEngine,
)
from atlas.services.sentinel.infrastructure_sources import (
    build_infrastructure_sources,
)
from atlas.services.sentinel.sources import (
    AtlasHealthSource,
    BackupSource,
    IncidentSource,
)


@dataclass(
    frozen=True,
    slots=True,
)
class SentinelSourceResult:
    source: str
    findings: tuple


@dataclass(
    frozen=True,
    slots=True,
)
class SentinelLiveResult:
    collected_at: datetime
    sources: tuple[
        SentinelSourceResult,
        ...
    ]
    evaluation: object


class SentinelLiveService:
    def __init__(
        self,
        *,
        sources=None,
        engine=None,
        clock=None,
    ):
        self.sources = (
            tuple(sources)
            if sources is not None
            else (
                (
                    IncidentSource(),
                    BackupSource(),
                    AtlasHealthSource(),
                )
                + build_infrastructure_sources()
            )
        )

        self.engine = (
            engine
            or SentinelEngine()
        )

        self.clock = (
            clock
            or (
                lambda:
                    datetime.now(UTC)
            )
        )

    def dry_run(
        self,
        *,
        previous_state=None,
    ):
        now = self.clock()

        source_results = []
        findings = []

        for source in self.sources:
            collected = tuple(
                source.collect(
                    observed_at=now
                )
            )

            source_results.append(
                SentinelSourceResult(
                    source=source.name,
                    findings=collected,
                )
            )

            findings.extend(
                collected
            )

        evaluation = (
            self.engine.evaluate(
                findings,
                previous_state or {},
                observed_at=now,
            )
        )

        return SentinelLiveResult(
            collected_at=now,
            sources=tuple(
                source_results
            ),
            evaluation=evaluation,
        )
