from dataclasses import dataclass, field


@dataclass
class IncidentTimeline:

    reasoning_timeline: list = field(default_factory=list)

    lifecycle: list = field(default_factory=list)
