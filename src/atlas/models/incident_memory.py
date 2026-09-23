from dataclasses import dataclass, field


@dataclass
class IncidentMemory:

    learning_context: dict = field(default_factory=dict)

    memory: dict = field(default_factory=dict)

    memory_intelligence: dict = field(default_factory=dict)
