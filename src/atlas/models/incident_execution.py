from dataclasses import dataclass, field


@dataclass
class IncidentExecution:

    safe_action: dict = field(default_factory=dict)

    approval_context: dict = field(default_factory=dict)

    approval_policy: dict = field(default_factory=dict)

    execution_context: dict = field(default_factory=dict)

    remediation_context: dict = field(default_factory=dict)
