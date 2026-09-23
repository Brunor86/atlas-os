from dataclasses import dataclass, field



@dataclass
class IntelligenceContext:


    infrastructure: dict = field(
        default_factory=dict
    )


    environment: dict = field(
        default_factory=dict
    )


    assets: list = field(
        default_factory=list
    )


    knowledge: object = None


    events: list = field(
        default_factory=list
    )


    incidents: list = field(
        default_factory=list
    )


    learning: list = field(
        default_factory=list
    )


    history: list = field(
        default_factory=list
    )




    operational_state: dict = field(
        default_factory=dict
    )

    ai_runtime: dict = field(
        default_factory=dict
    )

    actions: list = field(
        default_factory=list
    )



    def _serialize_ai_runtime(self):
        """
        Serialize AIModelRuntime into JSON-safe operational context.
        """
        runtime = self.ai_runtime

        if runtime is None:
            return {}

        models = []

        try:
            states = runtime.status()
        except Exception:
            states = []

        for state in states:
            models.append({
                "model": getattr(
                    state,
                    "model",
                    "",
                ),
                "provider_model": getattr(
                    state,
                    "provider_model",
                    None,
                ),
                "installed": bool(
                    getattr(
                        state,
                        "installed",
                        False,
                    )
                ),
                "loaded": bool(
                    getattr(
                        state,
                        "loaded",
                        False,
                    )
                ),
                "loaded_at": (
                    getattr(
                        state,
                        "loaded_at",
                        None,
                    ).isoformat()
                    if getattr(
                        state,
                        "loaded_at",
                        None,
                    )
                    else None
                ),
                "requests": getattr(
                    state,
                    "requests",
                    0,
                ),
                "successes": getattr(
                    state,
                    "successes",
                    0,
                ),
                "failures": getattr(
                    state,
                    "failures",
                    0,
                ),
                "last_error": getattr(
                    state,
                    "last_error",
                    None,
                ),
                "last_latency_ms": getattr(
                    state,
                    "last_latency_ms",
                    0,
                ),
                "health": (
                    state.health()
                    if hasattr(
                        state,
                        "health",
                    )
                    else "UNKNOWN"
                ),
            })

        return {
            "models": models,
            "count": len(models),
        }


    def to_dict(self):

        return {

            "infrastructure": self.infrastructure,

            "environment": self.environment,

            "assets": self.assets,

            "knowledge": self.knowledge,

            "events": self.events,

            "incidents": self.incidents,

            "learning": self.learning,

            "history": self.history,

            "operational_state": self.operational_state,
            "ai_runtime": self._serialize_ai_runtime(),

            "actions": self.actions,

        }





@dataclass
class IntelligenceResult:


    state: str = "UNKNOWN"




    #
    # Structured diagnostic conclusions generated
    # by the intelligence reasoning pipeline.
    #
    # Multiple diagnoses are allowed because one asset
    # may exhibit several independent conditions.
    #
    diagnoses: list = field(
        default_factory=list
    )

    diagnosis: dict = field(
        default_factory=dict
    )


    reasoning: list = field(
        default_factory=list
    )


    risks: list = field(
        default_factory=list
    )


    recommended_actions: list = field(
        default_factory=list
    )



    def to_dict(self):

        return {

            "state": self.state,


            "diagnoses": self.diagnoses,
            "diagnosis": self.diagnosis,

            "reasoning": self.reasoning,

            "risks": self.risks,

            "recommended_actions": self.recommended_actions,

        }
