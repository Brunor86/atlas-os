from uuid import uuid4

from atlas.services.ai.operator.execution import (
    OperatorExecution,
    OperatorExecutionStatus,
)

from atlas.services.ai.operator.models import (
    AIModelCapabilities,
    AIModelProfile,
)



class AIModelOperator:

    TASK_CAPABILITY = {
        "diagnosis": "reasoning",
        "root_cause": "reasoning",
        "incident_reasoning": "reasoning",
        "recommendation": "reasoning",
        "reasoning": "reasoning",
        "summary": "summary",
        "report": "summary",
        "coding": "coding",
        "development": "coding",
        "code_review": "coding",
    }


    def __init__(
        self,
        tool_registry=None,
    ):

        self.models = []

        self.tool_registry = tool_registry

        self.tools = []

        self._register_defaults()

        if tool_registry is not None:
            self._register_tools(
                tool_registry
            )


    def create_execution(
        self,
        task: str,
    ) -> OperatorExecution:

        return OperatorExecution(
            execution_id=str(uuid4()),
            task=task,
        )


    def update_execution(
        self,
        execution: OperatorExecution,
        status: OperatorExecutionStatus,
        *,
        model=None,
        error=None,
    ) -> OperatorExecution:

        execution.status = status

        if model is not None:
            execution.model = model.name
            execution.provider = model.provider
            execution.provider_model = model.provider_model

        if error is not None:
            execution.error = error

        return execution

    def _register_defaults(self):

        self.models.append(

            AIModelProfile(

                name="qwen_reasoning_9b",

                provider="ollama",

                provider_model="qwen3.5:9b",

                capabilities=AIModelCapabilities(

                    reasoning=True,

                    summary=False,

                    coding=False,

                    context_window=32768,

                    parameter_size="7B",

                ),

            )

        )


        self.models.append(

            AIModelProfile(

                name="qwen_summary",

                provider="ollama",

                provider_model="qwen2.5:7b",

                capabilities=AIModelCapabilities(

                    reasoning=False,

                    summary=True,

                    coding=False,

                    context_window=16384,

                    parameter_size="7B",

                ),

            )

        )


        self.models.append(

            AIModelProfile(

                name="qwen_coder",

                provider="ollama",

                provider_model="qwen2.5-coder:7b",

                capabilities=AIModelCapabilities(

                    reasoning=False,

                    summary=False,

                    coding=True,

                    context_window=32768,

                    parameter_size="7B",

                ),

            )

        )


        # ----------------------------------------------------
        # Heavy fallback models.
        #
        # These are NEVER selected before the normal 7B model.
        # They are invoked only when the primary model fails.
        # ----------------------------------------------------

        self.models.append(

            AIModelProfile(

                name="qwen_reasoning_14b",

                provider="ollama",

                provider_model="qwen2.5:14b",

                capabilities=AIModelCapabilities(

                    reasoning=True,

                    summary=True,

                    coding=False,

                    context_window=32768,

                    parameter_size="14B",

                ),

                priority=200,

                fallback_for="qwen_reasoning_9b",

            )

        )


        self.models.append(

            AIModelProfile(

                name="qwen_summary_14b",

                provider="ollama",

                provider_model="qwen2.5:14b",

                capabilities=AIModelCapabilities(

                    reasoning=True,

                    summary=True,

                    coding=False,

                    context_window=32768,

                    parameter_size="14B",

                ),

                priority=200,

                fallback_for="qwen_summary",

            )

        )


    def discover_models(
        self,
        provider_models: dict[str, list[str]],
    ):
        """
        Discover supported models exposed by providers.

        Discovery is intentionally conservative: only models for
        which ATLAS has an explicit capability profile are added.
        """

        known = {
            (
                model.provider,
                model.provider_model,
            )
            for model in self.models
        }

        discovered = []

        for provider, models in provider_models.items():

            for provider_model in models:

                if (
                    provider,
                    provider_model,
                ) in known:
                    continue

                # ------------------------------------------------
                # Qwen 3.5 9B
                # ------------------------------------------------

                if provider_model == "qwen3.5:9b":

                    profile = AIModelProfile(

                        name="qwen_reasoning_9b",

                        provider=provider,

                        provider_model=provider_model,

                        capabilities=AIModelCapabilities(

                            reasoning=True,

                            summary=True,

                            coding=False,

                            context_window=262144,

                            parameter_size="9.7B",

                        ),

                        priority=50,

                        fallback_for=None,

                    )

                    self.models.append(profile)

                    discovered.append(profile)

                    known.add(
                        (
                            provider,
                            provider_model,
                        )
                    )

        return discovered


    def _register_tools(
        self,
        tool_registry,
    ):

        from atlas.services.ai.operator.tools.intelligence import (
            IntelligenceToolBridge,
        )

        bridge = IntelligenceToolBridge(
            tool_registry
        )

        self.tools = bridge.tools()


    def list_tools(self):

        return self.tools


    def get_tool(
        self,
        name: str,
    ):

        for tool in self.tools:

            if tool.name == name:
                return tool

        return None


    def execute_tool(
        self,
        name: str,
        **kwargs,
    ):

        tool = self.get_tool(
            name
        )

        if not tool:

            from atlas.services.ai.operator.tools.base import (
                OperatorToolResult,
            )

            return OperatorToolResult(
                tool=name,
                success=False,
                error=f"Unknown AI operator tool: {name}",
            )

        return tool.execute(
            **kwargs
        )


    def list_models(self):

        return self.models


    def register_runtime(
        self,
        runtime,
    ):

        for model in self.models:

            runtime.register(
                model.name,
                model.provider_model,
            )


    def capability_for_task(
        self,
        task: str,
    ):

        return self.TASK_CAPABILITY.get(
            task,
            "summary",
        )


    def select(
        self,
        task: str,
        runtime,
        execution: OperatorExecution | None = None,
    ):

        if execution is not None:
            self.update_execution(
                execution,
                OperatorExecutionStatus.SELECTING_MODEL,
            )

        capability = self.capability_for_task(
            task
        )

        candidates = self.find_by_capability(
            capability
        )

        # Primary models always win.
        candidates = sorted(
            candidates,
            key=lambda model: (
                model.priority,
                model.name,
            ),
        )

        for model in candidates:

            # Heavy fallback models are not selected during
            # the normal pass. They are explicitly requested
            # by fallback_candidates().
            if model.fallback_for:
                continue

            if self.can_use(
                model.name,
                runtime,
            ):

                if execution is not None:
                    self.update_execution(
                        execution,
                        OperatorExecutionStatus.MODEL_SELECTED,
                        model=model,
                    )

                return model

        if execution is not None:
            self.update_execution(
                execution,
                OperatorExecutionStatus.FAILED,
                error="no_available_model",
            )

        return None


    def fallback_candidates(
        self,
        model,
        runtime,
    ):

        candidates = [

            candidate

            for candidate in self.models

            if (
                candidate.fallback_for == model.name
                and self.can_use(
                    candidate.name,
                    runtime,
                )
            )

        ]

        return sorted(
            candidates,
            key=lambda item: (
                item.priority,
                item.name,
            ),
        )


    def can_use(
        self,
        model_name: str,
        runtime,
    ):

        state = None

        for item in runtime.status():

            if item.model == model_name:

                state = item

                break


        if not state:

            return False


        return state.installed


    def find_by_capability(
        self,
        capability: str,
    ):

        return [

            model

            for model in self.models

            if getattr(
                model.capabilities,
                capability,
                False,
            )

        ]


    def status(
        self,
        runtime,
    ):
        return [
            {
                "name": model.name,
                "model": model.name,
                "provider": model.provider,
                "provider_model": model.provider_model,
                "installed": self.can_use(
                    model.name,
                    runtime,
                ),
                "priority": model.priority,
                "fallback_for": model.fallback_for,
            }
            for model in self.models
        ]


    def explain(
        self,
        task: str,
        runtime,
    ):

        capability = self.capability_for_task(
            task
        )

        candidates = self.find_by_capability(
            capability
        )

        if not candidates:
            return {
                "available": False,
                "reason": "no_capable_model_found",
                "task": task,
                "capability": capability,
            }

        # ----------------------------------------------------
        # Explain exactly the same routing hierarchy used by
        # the operator:
        #
        #   primary -> fallback candidates
        #
        # Heavy fallback models are never considered primary.
        # ----------------------------------------------------

        primary_candidates = sorted(
            (
                model
                for model in candidates
                if model.fallback_for is None
            ),
            key=lambda model: (
                model.priority,
                model.name,
            ),
        )

        # First: normal primary routing.
        for model in primary_candidates:

            if self.can_use(
                model.name,
                runtime,
            ):
                return {
                    "available": True,
                    "model": model.name,
                    "provider_model": model.provider_model,
                    "task": task,
                    "capability": capability,
                    "fallback": False,
                }

        # Second: explicit fallback routing.
        for model in primary_candidates:

            fallbacks = self.fallback_candidates(
                model,
                runtime,
            )

            if fallbacks:

                selected = fallbacks[0]

                return {
                    "available": True,
                    "model": selected.name,
                    "provider_model": selected.provider_model,
                    "task": task,
                    "capability": capability,
                    "fallback": True,
                    "primary_model": model.name,
                }

        unavailable_model = (
            primary_candidates[0]
            if primary_candidates
            else None
        )

        return {
            "available": False,
            "reason": "model_not_installed",
            "model": (
                unavailable_model.name
                if unavailable_model
                else None
            ),
            "provider_model": (
                unavailable_model.provider_model
                if unavailable_model
                else None
            ),
            "task": task,
            "capability": capability,
        }
