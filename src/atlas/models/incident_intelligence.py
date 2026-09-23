from dataclasses import dataclass, field


@dataclass
class IncidentIntelligence:

    reasoning: dict = field(default_factory=dict)

    recommendation: dict = field(default_factory=dict)

    memory: dict = field(default_factory=dict)

    memory_intelligence: dict = field(default_factory=dict)

    decision: dict = field(default_factory=dict)

    dependency_impact: dict = field(default_factory=dict)

    safe_action: dict = field(default_factory=dict)

    approval_policy: dict = field(default_factory=dict)

    approval_context: dict = field(default_factory=dict)

    execution_context: dict = field(default_factory=dict)

    remediation_context: dict = field(default_factory=dict)

    learning_context: dict = field(default_factory=dict)

    reasoning_timeline: list = field(default_factory=list)

    lifecycle: list = field(default_factory=list)


    def to_dict(self):

        return {

            "reasoning": self.reasoning,

            "recommendation": self.recommendation,

            "memory": self.memory,

            "memory_intelligence": self.memory_intelligence,

            "decision": self.decision,

            "dependency_impact": self.dependency_impact,

            "safe_action": self.safe_action,

            "approval_policy": self.approval_policy,

            "approval_context": self.approval_context,

            "execution_context": self.execution_context,

            "remediation_context": self.remediation_context,

            "learning_context": self.learning_context,

            "reasoning_timeline": self.reasoning_timeline,

            "lifecycle": self.lifecycle,

        }
