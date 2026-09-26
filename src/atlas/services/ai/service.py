import time


import json

from atlas.services.ai.models import (
    AIRequest,
    LLMResponse,
)

from atlas.services.ai.llm.ollama import OllamaProvider
from atlas.services.ai.runtime import AIModelRuntime
from atlas.services.ai.health import AIRuntimeHealth
from atlas.services.ai.target import AIRuntimeTarget
from atlas.services.ai.discovery import AIModelDiscovery
from atlas.config.ai import get_ollama_config

from atlas.services.context.operational import (
    OperationalContextBuilder,
)
from atlas.services.ai.prompts import AIPromptBuilder

from atlas.services.ai.operator.operator import (
    AIModelOperator,
)

from atlas.services.ai.operator.execution_service import (
    OperatorExecutionService,
)

from atlas.services.intelligence.operator_tools.factory import (
    build_operator_tool_registry,
)

from atlas.services.ai.reasoning_gate import AIReasoningGate
from atlas.services.ai.context import AIContextBuilder
from atlas.services.semantic.query import SemanticQueryEngine
from atlas.services.intelligence.operator_tools.synthesis import (
    can_synthesize_tool,
    synthesize_verified_tool_results,
)




def _is_operation_candidate(
    user_request,
) -> bool:
    """
    Conservative deterministic routing hint.

    This function does NOT authorize an operation and does NOT decide
    the action or target.

    It only prevents read-only deterministic preflights from consuming
    a request that contains an explicit operational command.

    PydanticOperationPlanner remains responsible for deciding whether
    the request is actually a supported operation.
    """

    import re
    import unicodedata

    normalized = unicodedata.normalize(
        "NFKD",
        str(
            user_request
            or ""
        ).casefold(),
    )

    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.combining(
            character
        )
    )

    tokens = set(
        re.findall(
            r"[a-z0-9_.@:-]+",
            normalized,
        )
    )

    operation_words = {
        "arranca",
        "arrancar",
        "inicia",
        "iniciar",
        "levanta",
        "levantar",
        "reinicia",
        "reiniciar",
        "detene",
        "detener",
        "apaga",
        "apagar",
        "start",
        "restart",
        "stop",
    }

    return bool(
        tokens
        & operation_words
    )



# ATLAS v0.126 · EXECUTABLE CAPABILITY GATE


def _canonical_execution_action(
    action,
    resource_type,
):

    verb = str(
        action
        or ""
    ).strip().lower()

    resource = str(
        resource_type
        or ""
    ).strip().lower()

    if (
        not verb
        or not resource
    ):
        return None

    return (
        verb
        + " "
        + resource
    )


def _operation_action_is_executable(
    action,
    resource_type,
):

    canonical_action = (
        _canonical_execution_action(
            action,
            resource_type,
        )
    )

    if not canonical_action:
        return False


    from atlas.services.intelligence.execution.service import (
        ActionExecutionService,
    )


    return (
        ActionExecutionService
        .is_action_executable(
            canonical_action
        )
    )


def _materialize_operation_plan(
    operation_plan,
    *,
    resolver=None,
):
    """
    Resolve a typed operational intent against authoritative
    ATLAS infrastructure identity.

    The LLM may preserve a human asset name such as olivasat
    or atlas-ai.

    This boundary converts that human target into the canonical
    resource type and execution target using deterministic
    Asset Registry knowledge.

    This function does not authorize or execute an operation.
    """

    intent = str(
        getattr(
            operation_plan,
            "intent",
            "",
        )
        or ""
    ).strip().upper()


    if intent != "PROPOSE":

        return {
            "status":
                "NOT_APPLICABLE",

            "requested_target":
                getattr(
                    operation_plan,
                    "target",
                    None,
                ),

            "resource_type":
                None,

            "target":
                None,

            "asset_id":
                None,

            "asset_name":
                None,

            "reason":
                "operation plan is not a proposal",

            "candidates":
                [],
        }


    from atlas.services.ai.operator.target_resolver import (
        OperationTargetResolver,
    )


    target_resolver = (
        resolver
        or OperationTargetResolver()
    )


    resolution = (
        target_resolver.resolve(
            getattr(
                operation_plan,
                "target",
                None,
            ),
            requested_resource_type=(
                getattr(
                    operation_plan,
                    "resource_type",
                    None,
                )
            ),
        )
    )


    return {
        "status":
            resolution.status,

        "requested_target":
            resolution.query,

        "resource_type":
            resolution.resource_type,

        "target":
            resolution.target,

        "asset_id":
            resolution.asset_id,

        "asset_name":
            resolution.asset_name,

        "reason":
            resolution.reason,

        "candidates":
            list(
                resolution.candidates
                or ()
            ),
    }


class AIService:


    def __init__(self):

        self.providers = {}

        self.runtime = AIModelRuntime()

        self.context_builder = AIContextBuilder()

        ollama_config = get_ollama_config()

        self.runtime_target = AIRuntimeTarget(
            name="local-ai",
            provider="ollama",
            host=ollama_config.host,
            port=ollama_config.port,
        )

        self.discovery = None

        # ----------------------------------------------------
        # ATLAS Operator tools
        #
        # Reuse the existing Intelligence ToolRegistry.
        # The AI layer does not access infrastructure directly.
        # ----------------------------------------------------

        self.tool_registry = (
            build_operator_tool_registry()
        )

        self.operator = AIModelOperator(
            tool_registry=self.tool_registry
        )

        # Register configured providers before model discovery.
        self._register_defaults()

        # Discover supported models exposed by configured providers.
        provider_models = {}

        for provider_name, provider in self.providers.items():

            try:
                provider_models[provider_name] = (
                    provider.models()
                )
            except Exception:
                provider_models[provider_name] = []

        discovered_models = self.operator.discover_models(
            provider_models
        )

        for model in discovered_models:
            self.runtime.register(
                model.name,
                model.provider_model,
            )

        # Newly discovered models were registered into Runtime
        # after the initial discovery scan. Refresh installed
        # state so dynamically discovered models become usable.
        self.discovery.scan()

        self.execution_service = (
            OperatorExecutionService(
                self.operator
            )
        )

        self.health = AIRuntimeHealth(
            self.runtime,
            self.runtime_target,
        )

        self.context_builder = OperationalContextBuilder(
            ai_runtime=self.runtime
        )
        self.prompt_builder = AIPromptBuilder()

        # Reasoning quality gate.
        # Validates structured reasoning before
        # ATLAS accepts the primary response.
        self.reasoning_gate = AIReasoningGate()


    def _register_defaults(self):

        self.operator.register_runtime(
            self.runtime
        )

        if self.runtime_target.provider == "ollama":

            self.providers["ollama"] = OllamaProvider(
                host=self.runtime_target.url.replace(
                    "ollama://",
                    "http://",
                    1,
                ),
            )

        self.discovery = AIModelDiscovery(
            self.operator,
            self.runtime,
            self.providers,
        )

        self.discovery.scan()


    def _select_model_with_refresh(
        self,
        task: str,
    ):
        """
        Select a model from the current runtime state.

        Model availability is normally discovered at AIService startup.
        When a remote provider such as Ollama was unavailable during
        startup, that installed state can become stale after the provider
        comes back.

        Refresh only after a selection miss, then retry exactly once.
        Healthy requests therefore incur no additional provider scan.
        """

        model = self.operator.select(
            task,
            self.runtime,
        )

        if model is not None:
            return model

        discovery = getattr(
            self,
            "discovery",
            None,
        )

        if discovery is None:
            return None

        try:
            discovery.scan()
        except Exception:
            return None

        return self.operator.select(
            task,
            self.runtime,
        )


    def list_tools(self):

        registry = getattr(
            self,
            "tool_registry",
            None,
        )

        if registry is None:
            return []

        return registry.describe()


    def execute_tool(
        self,
        name,
        **kwargs,
    ):

        return self.operator.execute_tool(
            name,
            **kwargs,
        )


    def ask_operator(
        self,
        request: AIRequest,
        *,
        event_callback=None,
    ) -> LLMResponse:
        """
        Execute the interactive read-only infrastructure operator.

        Pipeline:

            deterministic semantic
                ->
            deterministic telemetry tool
                ->
            persistent LLM planner session
                ->
            MCP knowledge agent

        The planner model is selected lazily and kept resident only
        for the duration of this single operator investigation.
        """

        from atlas.mcp.client import (
            MCPKnowledgeClient,
        )

        from atlas.services.ai.agent.agent import (
            OperatorAgent,
        )

        start = time.perf_counter()

        planner_state = {
            "model":
                None,

            "provider":
                None,

            "calls":
                0,
        }


        def planner(
            planner_request: AIRequest,
        ) -> LLMResponse:
            """
            Execute one agent planning decision while keeping the same
            physical Ollama model resident across MCP investigation
            steps.
            """

            model = planner_state[
                "model"
            ]

            provider = planner_state[
                "provider"
            ]

            # --------------------------------------------------------
            # Lazy model selection.
            #
            # Deterministic semantic/tool requests never reach this
            # function, so they never load an LLM.
            # --------------------------------------------------------

            if model is None:

                model = self._select_model_with_refresh(
                    planner_request.task,
                )

                if model is None:
                    raise RuntimeError(
                        "No model available for "
                        "MCP knowledge planner"
                    )

                provider = self.providers.get(
                    model.provider
                )

                if provider is None:
                    raise RuntimeError(
                        "Provider unavailable for "
                        f"MCP planner: {model.provider}"
                    )

                if not provider.available():
                    raise RuntimeError(
                        "MCP planner provider unavailable"
                    )

                planner_state[
                    "model"
                ] = model

                planner_state[
                    "provider"
                ] = provider

                self.runtime.load(
                    model.name
                )

                print(
                    "[AI AGENT PLANNER] "
                    "session=start "
                    f"model={model.name} "
                    f"provider_model={model.provider_model}"
                )


            planner_state[
                "calls"
            ] += 1

            call_number = planner_state[
                "calls"
            ]

            self.runtime.record_request(
                model.name
            )

            call_start = (
                time.perf_counter()
            )

            try:

                if isinstance(provider, OllamaProvider):

                    result = provider.generate(
                        planner_request.user_prompt,
                        model=model.provider_model,
                        temperature=(
                            planner_request.temperature
                        ),
                        max_tokens=(
                            planner_request.max_tokens
                        ),

                        # Keep the physical model resident between MCP
                        # planning steps. ask_operator() explicitly
                        # unloads it in its final cleanup boundary.
                        think=False,
                        keep_alive="5m",
                    )

                else:

                    result = provider.generate(
                        planner_request.user_prompt,
                        model=model.provider_model,
                        temperature=(
                            planner_request.temperature
                        ),
                        max_tokens=(
                            planner_request.max_tokens
                        ),

                        # Keep the physical model resident between MCP
                        # planning steps. ask_operator() explicitly
                        # unloads it in its final cleanup boundary.
                        keep_alive="5m",
                    )

                elapsed_ms = (
                    time.perf_counter()
                    - call_start
                ) * 1000

                if (
                    not result
                    or not result.strip()
                ):
                    raise RuntimeError(
                        "MCP planner returned "
                        "an empty response"
                    )

                self.runtime.record_success(
                    model.name,
                    round(
                        elapsed_ms,
                        2,
                    ),
                )

                print(
                    "[AI AGENT PLANNER] "
                    f"call={call_number} "
                    f"reused={call_number > 1} "
                    f"generate={elapsed_ms / 1000:.2f}s"
                )

                return LLMResponse(
                    model=model.name,
                    provider=model.provider,
                    content=result,
                    latency_ms=round(
                        elapsed_ms,
                        2,
                    ),
                    metadata={
                        "agent_protocol":
                            True,

                        "minimal_context":
                            True,

                        "persistent_session":
                            True,

                        "planner_call":
                            call_number,

                        "tools_used":
                            [],

                        "llm_used":
                            True,
                    },
                )

            except Exception as exc:

                elapsed_ms = (
                    time.perf_counter()
                    - call_start
                ) * 1000

                self.runtime.record_failure(
                    model.name,
                    str(exc),
                    round(
                        elapsed_ms,
                        2,
                    ),
                )

                raise


        operation_candidate = (
            _is_operation_candidate(
                request.user_prompt
            )
        )

        if operation_candidate:

            print(
                "[AI OPERATION ROUTER] "
                "candidate=true "
                "route=operation_planner "
                "knowledge_agent=bypass"
            )


        agent = OperatorAgent(
            self,
            max_steps=6,
            tool_backend=MCPKnowledgeClient(),
            planner=planner,
            semantic_preflight=(
                not operation_candidate
            ),
            tool_preflight=(
                not operation_candidate
            ),
            event_callback=event_callback,
        )

        try:

            # --------------------------------------------------------
            # EXPLICIT OPERATION ROUTING
            #
            # An explicit supported operation must not be investigated
            # first by the read-only Knowledge Agent.
            #
            # The operation planner interprets only the requested
            # operation. ATLAS then resolves the target deterministically
            # and the governed Operator creates, at most, a proposal.
            #
            # No execution authority is granted here.
            # --------------------------------------------------------

            if operation_candidate:

                operation_model = (
                    self._select_model_with_refresh(
                        request.task
                    )
                )

                if operation_model is None:

                    raise RuntimeError(
                        "No model available for "
                        "operation planner"
                    )


                operation_provider = (
                    self.providers.get(
                        operation_model.provider
                    )
                )

                if operation_provider is None:

                    raise RuntimeError(
                        "Provider unavailable for "
                        "operation planner: "
                        + str(
                            operation_model.provider
                        )
                    )


                if not operation_provider.available():

                    raise RuntimeError(
                        "Operation planner provider unavailable"
                    )


                planner_state[
                    "model"
                ] = operation_model

                planner_state[
                    "provider"
                ] = operation_provider


                self.runtime.load(
                    operation_model.name
                )


                result = {
                    "status":
                        "SUCCESS",

                    "answer":
                        "",

                    "steps":
                        0,

                    "model":
                        operation_model.name,

                    "provider":
                        operation_model.provider,

                    "llm_used":
                        True,

                    "tools_used":
                        [],

                    "observations":
                        [],
                }


                print(
                    "[AI OPERATION ROUTER] "
                    "knowledge_agent=false "
                    "operation_planner=true"
                )


            else:

                result = agent.run(
                    request.user_prompt
                )


            # --------------------------------------------------------
            # ATLAS OPERATION PLANNING BOUNDARY
            #
            # The knowledge agent above remains strictly read-only.
            #
            # Only after that investigation has completed may a
            # separate typed PydanticAI planner interpret whether the
            # user explicitly requested a supported operation.
            #
            # Even then, the AI receives no execution capability.
            #
            # OperationPlan
            #     ->
            # atlas-operator MCP
            #     ->
            # PENDING_APPROVAL
            #
            # Human approval and execution remain outside the LLM.
            # --------------------------------------------------------

            if (
                operation_candidate
                or (
                    int(
                        planner_state[
                            "calls"
                        ]
                        or 0
                    )
                    > 0
                )
            ):

                try:

                    from atlas.mcp.operator_client import (
                        MCPOperatorClient,
                    )

                    from atlas.services.ai.operator.pydantic_planner import (
                        PydanticOperationPlanner,
                    )


                    operation_model = (
                        planner_state[
                            "model"
                        ]
                    )


                    if (
                        operation_model
                        is not None
                    ):

                        base_url = (
                            self.runtime_target.url
                            .replace(
                                "ollama://",
                                "http://",
                                1,
                            )
                            .rstrip("/")
                            + "/v1"
                        )


                        operation_planner = (
                            PydanticOperationPlanner
                            .for_ollama(
                                model_name=(
                                    operation_model
                                    .provider_model
                                ),
                                base_url=base_url,
                            )
                        )


                        operation_plan = (
                            operation_planner.plan(
                                request.user_prompt,
                                observations=list(
                                    result.get(
                                        "observations",
                                        [],
                                    )
                                    or []
                                ),
                            )
                        )


                        print(
                            "[AI OPERATION PLANNER] "
                            f"intent={operation_plan.intent} "
                            f"resource_type={operation_plan.resource_type} "
                            f"action={operation_plan.action} "
                            f"target={operation_plan.target} "
                            f"confidence={operation_plan.confidence:.2f}"
                        )


                        requested_operation_plan = (
                            operation_plan.model_dump()
                        )


                        operation_materialized = (
                            _materialize_operation_plan(
                                operation_plan
                            )
                        )


                        if (
                            operation_materialized.get(
                                "status"
                            )
                            == "RESOLVED"
                        ):

                            operation_plan = (
                                operation_plan.model_copy(
                                    update={
                                        "resource_type":
                                            operation_materialized.get(
                                                "resource_type"
                                            ),

                                        "target":
                                            operation_materialized.get(
                                                "target"
                                            ),
                                    }
                                )
                            )


                            print(
                                "[AI OPERATION TARGET] "
                                "status=RESOLVED "
                                f"requested={operation_materialized.get("requested_target")} "
                                f"asset={operation_materialized.get("asset_name")} "
                                f"resource_type={operation_plan.resource_type} "
                                f"target={operation_plan.target}"
                            )


                        else:

                            print(
                                "[AI OPERATION TARGET] "
                                f"status={operation_materialized.get("status")} "
                                f"requested={operation_materialized.get("requested_target")} "
                                f"reason={operation_materialized.get("reason")}"
                            )


                        canonical_execution_action = (
                            _canonical_execution_action(
                                operation_plan.action,
                                operation_plan.resource_type,
                            )
                        )

                        operation_executable = (
                            _operation_action_is_executable(
                                operation_plan.action,
                                operation_plan.resource_type,
                            )
                        )


                        if (
                            operation_plan.intent
                            == "PROPOSE"
                            and operation_plan.confidence
                            >= 0.80
                            and operation_materialized.get(
                                "status"
                            )
                            != "RESOLVED"
                        ):

                            blocked_reason = (
                                "target resolution "
                                + str(
                                    operation_materialized.get(
                                        "status",
                                        "FAILED",
                                    )
                                )
                                + ": "
                                + str(
                                    operation_materialized.get(
                                        "reason",
                                        "target could not be resolved",
                                    )
                                )
                            )


                            candidates = (
                                operation_materialized.get(
                                    "candidates",
                                    []
                                )
                                or []
                            )


                            if candidates:

                                blocked_reason += (
                                    " · candidates="
                                    + ", ".join(
                                        str(item)
                                        for item
                                        in candidates
                                    )
                                )


                            result[
                                "answer"
                            ] = (
                                "ATLAS could not resolve "
                                "the requested operation target: "
                                + blocked_reason
                            )


                            if (
                                event_callback
                                is not None
                            ):

                                try:

                                    event_callback(
                                        "operation_blocked",
                                        {
                                            "message":
                                                blocked_reason,

                                            "plan":
                                                requested_operation_plan,

                                            "target_resolution":
                                                operation_materialized,
                                        },
                                    )

                                except Exception:

                                    pass


                            print(
                                "[AI OPERATION PLANNER] "
                                "proposal=false "
                                f"reason={blocked_reason}"
                            )


                        elif (
                            operation_plan.intent
                            == "PROPOSE"
                            and operation_plan.confidence
                            >= 0.80
                            and operation_plan.resource_type
                            in (
                                "container",
                                "service",
                                "vm",
                                "lxc",
                            )
                            and operation_executable
                        ):

                            operator_client = (
                                MCPOperatorClient()
                            )


                            proposal_tool = {
                                "container":
                                    "atlas_propose_container_action",

                                "service":
                                    "atlas_propose_service_action",

                                "vm":
                                    "atlas_propose_proxmox_guest_action",

                                "lxc":
                                    "atlas_propose_proxmox_guest_action",
                            }[
                                operation_plan.resource_type
                            ]


                            proposal_arguments = {
                                "action":
                                    operation_plan.action,

                                "target":
                                    operation_plan.target,
                            }


                            if (
                                operation_plan.resource_type
                                in (
                                    "vm",
                                    "lxc",
                                )
                            ):

                                proposal_arguments[
                                    "resource_type"
                                ] = (
                                    operation_plan.resource_type
                                )


                            proposal_result = (
                                operator_client
                                .execute_tool(
                                    proposal_tool,
                                    **proposal_arguments,
                                )
                            )


                            if (
                                proposal_result.success
                            ):

                                proposal = dict(
                                    proposal_result.data
                                    or {}
                                )

                                proposal[
                                    "plan"
                                ] = (
                                    operation_plan
                                    .model_dump()
                                )


                                proposal[
                                    "requested_plan"
                                ] = (
                                    requested_operation_plan
                                )


                                proposal[
                                    "target_resolution"
                                ] = (
                                    operation_materialized
                                )


                                result[
                                    "status"
                                ] = (
                                    "PENDING_APPROVAL"
                                )

                                result[
                                    "answer"
                                ] = (
                                    "ATLAS prepared an "
                                    "operation proposal. "
                                    "Human approval is required "
                                    "before execution."
                                )

                                result[
                                    "operation_proposal"
                                ] = proposal


                                if (
                                    event_callback
                                    is not None
                                ):

                                    try:

                                        event_callback(
                                            "operation_proposed",
                                            proposal,
                                        )

                                    except Exception:

                                        pass


                                print(
                                    "[AI OPERATION PLANNER] "
                                    "proposal=true "
                                    f"action_id="
                                    f"{proposal.get('action_request', {}).get('id')}"
                                )


                            else:

                                result[
                                    "answer"
                                ] = (
                                    "ATLAS blocked the "
                                    "requested operation: "
                                    + str(
                                        proposal_result.error
                                        or "operation proposal failed"
                                    )
                                )


                                if (
                                    event_callback
                                    is not None
                                ):

                                    try:

                                        event_callback(
                                            "operation_blocked",
                                            {
                                                "message":
                                                    proposal_result.error,

                                                "plan":
                                                    operation_plan.model_dump(),
                                            },
                                        )

                                    except Exception:

                                        pass


                                print(
                                    "[AI OPERATION PLANNER] "
                                    "proposal=false "
                                    f"reason={proposal_result.error}"
                                )


                        elif (
                            operation_plan.intent
                            == "PROPOSE"
                            and operation_plan.confidence
                            >= 0.80
                            and operation_plan.resource_type
                            in (
                                "container",
                                "service",
                                "vm",
                                "lxc",
                            )
                            and not operation_executable
                        ):

                            blocked_reason = (
                                "execution capability unavailable for action: "
                                + str(
                                    canonical_execution_action
                                )
                            )

                            result[
                                "answer"
                            ] = (
                                "ATLAS blocked the "
                                "requested operation: "
                                + blocked_reason
                            )

                            if (
                                event_callback
                                is not None
                            ):

                                try:

                                    event_callback(
                                        "operation_blocked",
                                        {
                                            "message":
                                                blocked_reason,

                                            "plan":
                                                operation_plan.model_dump(),
                                        },
                                    )

                                except Exception:

                                    pass

                            print(
                                "[AI OPERATION PLANNER] "
                                "proposal=false "
                                f"reason={blocked_reason}"
                            )


                        elif (
                            operation_plan.intent
                            == "PROPOSE"
                            and operation_plan.confidence
                            >= 0.80
                        ):

                            blocked_reason = (
                                "unsupported operational resource type: "
                                + str(
                                    operation_plan.resource_type
                                )
                            )

                            result[
                                "answer"
                            ] = (
                                "ATLAS blocked the "
                                "requested operation: "
                                + blocked_reason
                            )

                            if (
                                event_callback
                                is not None
                            ):

                                try:

                                    event_callback(
                                        "operation_blocked",
                                        {
                                            "message":
                                                blocked_reason,

                                            "plan":
                                                operation_plan.model_dump(),
                                        },
                                    )

                                except Exception:

                                    pass

                            print(
                                "[AI OPERATION PLANNER] "
                                "proposal=false "
                                f"reason={blocked_reason}"
                            )


                        elif (
                            operation_plan.intent
                            == "PROPOSE"
                        ):

                            print(
                                "[AI OPERATION PLANNER] "
                                "proposal=false "
                                "reason=confidence_below_threshold"
                            )


                except Exception as operation_exc:

                    #
                    # Operation planning is an additive capability.
                    # Failure here must never break the existing
                    # read-only Ask ATLAS path.
                    #
                    print(
                        "[AI OPERATION PLANNER] "
                        "error="
                        + str(
                            operation_exc
                        )
                    )


        finally:

            # --------------------------------------------------------
            # HARD PHYSICAL MEMORY BOUNDARY FOR MCP PLANNER
            #
            # The same model is reused inside this investigation but
            # must not survive after ask_operator() finishes.
            # --------------------------------------------------------

            planner_model = (
                planner_state[
                    "model"
                ]
            )

            if planner_model is not None:

                try:

                    self._unload_model(
                        planner_model
                    )

                    print(
                        "[AI AGENT PLANNER] "
                        "session=end "
                        "unloaded=true"
                    )

                except Exception as cleanup_exc:

                    print(
                        "[AI AGENT PLANNER] "
                        "session=end "
                        "unloaded=false "
                        f"error={cleanup_exc}"
                    )

            self.runtime.unload_all()


        latency_ms = (
            time.perf_counter()
            - start
        ) * 1000

        observations = list(
            result.get(
                "observations",
                [],
            )
        )

        tools_used = list(
            result.get(
                "tools_used",
                [],
            )
        )

        # --------------------------------------------------------
        # Execution mode is determined by the path actually taken,
        # never by tool naming.
        #
        # Native deterministic capabilities may legitimately use
        # atlas_* names without involving MCP or an LLM.
        # --------------------------------------------------------

        planner_calls = int(
            planner_state[
                "calls"
            ]
            or 0
        )

        llm_used = bool(
            result.get(
                "llm_used"
            )
        )

        deterministic = (
            planner_calls == 0
            and not llm_used
        )

        mcp_agent = (
            planner_calls > 0
        )

        print(
            "[AI OPERATOR] "
            f"status={result.get('status')} "
            f"steps={result.get('steps')} "
            f"planner_calls={planner_calls} "
            f"mcp={mcp_agent} "
            f"tools={','.join(tools_used)} "
            f"latency={latency_ms:.2f}ms"
        )

        return LLMResponse(
            model=(
                result.get(
                    "model"
                )
                or (
                    "atlas-mcp-agent"
                    if mcp_agent
                    else "atlas-operator"
                )
            ),
            provider=(
                result.get(
                    "provider"
                )
                or (
                    "atlas"
                    if not result.get(
                        "llm_used"
                    )
                    else "ollama"
                )
            ),
            content=(
                result.get(
                    "answer"
                )
                or result.get(
                    "error"
                )
                or (
                    "ATLAS could not resolve "
                    "the request."
                )
            ),
            latency_ms=round(
                latency_ms,
                2,
            ),
            metadata={
                "fallback":
                    False,

                "operator":
                    True,

                "deterministic":
                    deterministic,

                "mcp_agent":
                    mcp_agent,

                "mcp_server":
                    (
                        "atlas-knowledge"
                        if mcp_agent
                        else None
                    ),

                "read_only":
                    True,

                "llm_used":
                    llm_used,

                "steps":
                    result.get(
                        "steps"
                    ),

                "planner_calls":
                    planner_calls,

                "persistent_planner_session":
                    bool(
                        planner_calls
                    ),

                "tools_used":
                    tools_used,

                "tool_calls":
                    observations,

                "agent_status":
                    result.get(
                        "status"
                    ),

                "context_mode":
                    (
                        "deterministic"
                        if deterministic
                        else (
                            "mcp_read_only"
                            if mcp_agent
                            else "operator"
                        )
                    ),
            },
        )


    def _unload_model(
        self,
        model,
    ):
        """
        Release the physical provider model and synchronize
        the ATLAS runtime state.
        """

        if not model:
            return

        provider = self.providers.get(
            model.provider
        )

        # Always synchronize ATLAS runtime state, even when
        # the provider does not expose physical unload.
        if provider is None:
            self.runtime.unload(
                model.name
            )
            return

        unload = getattr(
            provider,
            "unload",
            None,
        )

        try:

            # Real providers such as Ollama implement unload().
            # Fake/test providers may not.
            if unload is not None:
                unload(
                    model.provider_model
                )

        finally:

            # Runtime state must always be synchronized,
            # regardless of provider capabilities or errors.
            self.runtime.unload(
                model.name
            )
    def ask(
        self,
        request: AIRequest,
    ) -> LLMResponse:

        # ----------------------------------------------------
        # Operator execution lifecycle
        # ----------------------------------------------------

        execution = self.execution_service.create(
            request,
        )

        model = self.execution_service.select_model(
            execution,
            request,
            self.runtime,
        )

        # ----------------------------------------------------
        # No suitable model.
        #
        # select_model() already marks the execution FAILED.
        # ----------------------------------------------------

        if not model:

            explanation = self.operator.explain(
                request.task,
                self.runtime,
            )

            response = LLMResponse(

                model=explanation.get(
                    "model",
                    "none",
                ),

                provider="ollama",

                content=(
                    "AI model unavailable. "
                    f"Required model "
                    f"{explanation.get('provider_model')} "
                    "is not installed."
                ),

                metadata={

                    "reason":
                        explanation.get(
                            "reason"
                        ),

                    "provider_model":
                        explanation.get(
                            "provider_model"
                        ),

                    "capability":
                        explanation.get(
                            "capability"
                        ),

                    "task":
                        request.task,

                    "execution_id":
                        execution.execution_id,

                    "execution_status":
                        execution.status.value,

                },

            )

            return response

        # ----------------------------------------------------
        # OperatorExecutionService owns EXECUTING /
        # COMPLETED / FAILED transitions.
        #
        # The existing AI execution engine remains unchanged
        # inside _execute_with_model().
        # ----------------------------------------------------

        response = self.execution_service.execute(
            execution,
            request,
            executor=lambda req: self._execute_with_model(
                req,
                model,
            ),
        )

        # ----------------------------------------------------
        # Attach execution identity to the response without
        # changing the existing LLM response contract.
        # ----------------------------------------------------

        response.metadata["execution_id"] = (
            execution.execution_id
        )

        response.metadata["execution_status"] = (
            execution.status.value
        )

        return response

    def _operator_tool_definitions(self):

        definitions = []

        for tool in self.operator.list_tools():

            definitions.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": self._tool_parameters(
                        tool.name
                    ),
                },
            })

        return definitions


    def _tool_parameters(
        self,
        name: str,
    ) -> dict:
        """
        Return the schema exposed by the runtime OperatorTool.

        AIService contains no concrete tool schemas.
        """

        for tool in self.operator.list_tools():

            if tool.name != name:
                continue

            parameters = getattr(
                tool,
                "parameters",
                None,
            )

            if isinstance(
                parameters,
                dict,
            ):
                return parameters

            break

        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    def _execute_operator_tool_calls(
        self,
        tool_calls,
    ):

        results = []

        for call in tool_calls:

            function = call.get(
                "function",
                {},
            )

            name = function.get(
                "name"
            )

            arguments = function.get(
                "arguments",
                {},
            )

            if isinstance(
                arguments,
                str,
            ):

                try:
                    arguments = json.loads(
                        arguments
                    )
                except Exception:
                    arguments = {}

            result = self.operator.execute_tool(
                name,
                **arguments,
            )

            results.append({
                "tool_call_id": call.get("id"),
                "name": name,
                "result": result.model_dump(
                    mode="json"
                ),
            })

        return results


    def _execute_routed_tools(
        self,
        tool_names,
    ):
        """
        Execute deterministically routed tools without asking
        the LLM to generate tool calls.
        """

        results = []

        for name in tool_names:

            result = self.operator.execute_tool(
                name
            )

            results.append(
                {
                    "tool_call_id": None,
                    "name": name,
                    "result": result.model_dump(
                        mode="json"
                    ),
                }
            )

        return results


    def _compact_tool_result(
        self,
        tool_name: str,
        result: dict,
    ) -> dict:
        """
        Delegate result compaction to the runtime tool contract.

        AIService contains no knowledge of concrete result schemas.
        """

        for tool in self.operator.list_tools():

            if tool.name != tool_name:
                continue

            compactor = getattr(
                tool,
                "compact_result",
                None,
            )

            if callable(
                compactor
            ):
                return compactor(
                    result
                )

            break

        return result

    def deterministic_semantic_query(
        self,
        user_prompt: str,
    ) -> dict | None:
        """
        Resolve high-confidence semantic infrastructure queries
        without invoking telemetry tools or an LLM.

        SemanticQueryEngine owns interpretation, asset resolution
        and deterministic execution.
        """

        if not isinstance(
            user_prompt,
            str,
        ):
            return None

        if not user_prompt.strip():
            return None

        try:

            engine = SemanticQueryEngine()

            plan = engine.plan(
                user_prompt
            )

        except Exception:
            return None

        confidence = float(
            getattr(
                plan,
                "confidence",
                0.0,
            )
            or 0.0
        )

        if confidence < 0.90:
            return None

        # ---------------------------------------------------------
        # Execute semantic query first.
        #
        # Do NOT rely on plan.operation here because operation is an
        # internal execution primitive while semantic.intent is the
        # stable user-facing semantic contract.
        # ---------------------------------------------------------

        try:

            result = engine.query(
                user_prompt
            )

        except Exception:
            return None

        if not isinstance(
            result,
            dict,
        ):
            return None

        if result.get(
            "status"
        ) != "SUCCESS":
            return None

        semantic = (
            result.get(
                "semantic"
            )
            or {}
        )

        intent = str(
            semantic.get(
                "intent",
                "",
            )
            or ""
        ).upper()

        deterministic_intents = {
            "INVENTORY",
            "TOPOLOGY",
            "RELATION",
            "IMPACT",
        }

        if intent not in deterministic_intents:
            return None

        print(
            "[AI SEMANTIC ROUTING] "
            f"intent={intent} "
            f"confidence={confidence:.2f}"
        )

        return result


    def synthesize_semantic_result(
        self,
        result: dict,
    ) -> str:
        """
        Produce a deterministic human-readable answer from a
        successful semantic result.

        No LLM is involved.
        """

        if not isinstance(
            result,
            dict,
        ):
            return ""

        semantic = (
            result.get(
                "semantic"
            )
            or {}
        )

        intent = str(
            semantic.get(
                "intent",
                "",
            )
            or ""
        ).upper()

        # ---------------------------------------------------------
        # INVENTORY
        # ---------------------------------------------------------

        if intent == "INVENTORY":

            assets = (
                result.get(
                    "assets"
                )
                or []
            )

            count = result.get(
                "count",
                len(assets),
            )

            asset_type = semantic.get(
                "asset_type"
            )

            status = semantic.get(
                "status"
            )

            filters = []

            if asset_type:
                filters.append(
                    str(
                        asset_type
                    )
                )

            if status:
                filters.append(
                    str(
                        status
                    )
                )

            description = (
                " ".join(
                    filters
                )
                if filters
                else "assets"
            )

            if not assets:

                return (
                    "No se encontraron assets "
                    f"{description}."
                )

            lines = []

            for asset in assets:

                if not isinstance(
                    asset,
                    dict,
                ):
                    continue

                name = (
                    asset.get("name")
                    or asset.get("id")
                    or "unknown"
                )

                current_status = (
                    asset.get("status")
                )

                line = (
                    f"- {name}"
                )

                if current_status:
                    line += (
                        f" [{current_status}]"
                    )

                lines.append(
                    line
                )

            return (
                f"Se encontraron {count} "
                f"assets {description}:\n"
                + "\n".join(
                    lines
                )
            )

        # ---------------------------------------------------------
        # EXACT GRAPH RELATION
        # ---------------------------------------------------------

        if intent == "RELATION":

            entity = (
                result.get(
                    "entity"
                )
                or {}
            )

            items = (
                result.get(
                    "results"
                )
                or []
            )

            relationship = (
                result.get(
                    "relationship"
                )
                or semantic.get(
                    "relationship"
                )
                or "RELATION"
            )

            orientation = (
                result.get(
                    "orientation"
                )
                or semantic.get(
                    "orientation"
                )
                or "OUTGOING"
            )

            label = (
                entity.get(
                    "group_value"
                )
                or entity.get(
                    "query"
                )
                or entity.get(
                    "asset_id"
                )
                or "entidad"
            )

            if not items:

                if (
                    relationship
                    == "DEPENDS_ON"
                    and orientation
                    == "OUTGOING"
                ):

                    return (
                        "ATLAS no registra "
                        "dependencias directas para "
                        f"{label}."
                    )

                if (
                    relationship
                    == "DEPENDS_ON"
                    and orientation
                    == "INCOMING"
                ):

                    return (
                        "ATLAS no registra assets "
                        "que dependan directamente de "
                        f"{label}."
                    )

                return (
                    "ATLAS no registra relaciones "
                    f"{relationship} para {label}."
                )

            lines = []

            for item in items:

                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                source = (
                    item.get(
                        "source_name"
                    )
                    or item.get(
                        "source_asset_id"
                    )
                    or "unknown"
                )

                target = (
                    item.get(
                        "target_name"
                    )
                    or item.get(
                        "target_asset_id"
                    )
                    or "unknown"
                )

                relation_type = (
                    item.get(
                        "relationship"
                    )
                    or relationship
                )

                if (
                    relation_type
                    == "DEPENDS_ON"
                ):

                    line = (
                        f"- {source} "
                        f"depende de {target}"
                    )

                else:

                    line = (
                        f"- {source} "
                        f"--{relation_type}--> "
                        f"{target}"
                    )

                lines.append(
                    line
                )

            if (
                relationship
                == "DEPENDS_ON"
                and orientation
                == "OUTGOING"
            ):

                heading = (
                    f"Dependencias directas de "
                    f"{label}"
                )

            elif (
                relationship
                == "DEPENDS_ON"
                and orientation
                == "INCOMING"
            ):

                heading = (
                    f"Dependientes directos de "
                    f"{label}"
                )

            else:

                heading = (
                    f"Relaciones {relationship} "
                    f"de {label}"
                )

            return (
                f"{heading}:\n"
                + "\n".join(
                    lines
                )
            )

        # ---------------------------------------------------------
        # TOPOLOGY
        # ---------------------------------------------------------

        if intent == "TOPOLOGY":

            asset = (
                result.get(
                    "asset"
                )
                or {}
            )

            name = (
                asset.get("name")
                or asset.get("id")
                or "asset"
            )

            direction = (
                result.get(
                    "direction"
                )
                or semantic.get(
                    "direction"
                )
                or "neighbors"
            )

            items = (
                result.get(
                    "results"
                )
                or []
            )

            lines = []

            for item in items:

                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                target = (
                    item.get(
                        "asset_id"
                    )
                    or "unknown"
                )

                relationship = (
                    item.get(
                        "relationship"
                    )
                )

                depth = item.get(
                    "depth"
                )

                line = (
                    f"- {target}"
                )

                details = []

                if relationship:
                    details.append(
                        str(
                            relationship
                        )
                    )

                if depth is not None:
                    details.append(
                        f"depth={depth}"
                    )

                if details:

                    line += (
                        " ["
                        + ", ".join(
                            details
                        )
                        + "]"
                    )

                lines.append(
                    line
                )

            if not lines:

                return (
                    f"No se encontraron relaciones "
                    f"{direction} para {name}."
                )

            return (
                f"{name}: "
                f"{len(items)} relaciones "
                f"{direction}:\n"
                + "\n".join(
                    lines
                )
            )

        # ---------------------------------------------------------
        # IMPACT
        # ---------------------------------------------------------

        if intent == "IMPACT":

            asset = (
                result.get(
                    "asset"
                )
                or {}
            )

            impact = (
                result.get(
                    "impact"
                )
                or {}
            )

            name = (
                asset.get("name")
                or asset.get("id")
                or "asset"
            )

            severity = (
                impact.get(
                    "severity"
                )
                or "UNKNOWN"
            )

            score = impact.get(
                "impact_score"
            )

            downstream = (
                impact.get(
                    "downstream"
                )
                or []
            )

            parts = [
                (
                    f"El impacto de una caída de "
                    f"{name} es {severity}"
                )
            ]

            if score is not None:

                parts.append(
                    f"impact_score={score}"
                )

            parts.append(
                (
                    f"{len(downstream)} assets "
                    "downstream afectados"
                )
            )

            return (
                ". ".join(
                    parts
                )
                + "."
            )

        return str(
            result
        )


    def _normalize_tool_routing_text(
        self,
        value: str,
    ) -> str:
        """
        Normalize human language for generic tool relevance scoring.

        This function contains no infrastructure-specific vocabulary.
        """

        import re
        import unicodedata

        value = str(
            value or ""
        ).lower()

        value = unicodedata.normalize(
            "NFKD",
            value,
        )

        value = "".join(
            character
            for character in value
            if not unicodedata.combining(
                character
            )
        )

        value = value.replace(
            "_",
            " ",
        )

        value = value.replace(
            "-",
            " ",
        )

        value = re.sub(
            r"[^a-z0-9\s]+",
            " ",
            value,
        )

        return " ".join(
            value.split()
        )


    def _tool_routing_tokens(
        self,
        value: str,
    ) -> list[str]:
        """
        Extract meaningful generic routing tokens.
        """

        normalized = (
            self._normalize_tool_routing_text(
                value
            )
        )

        # Language glue only.
        # No infrastructure concepts belong here.
        stopwords = {
            "a",
            "al",
            "an",
            "and",
            "about",
            "como",
            "con",
            "cual",
            "cuales",
            "cuanto",
            "cuantos",
            "de",
            "del",
            "do",
            "does",
            "el",
            "en",
            "es",
            "esta",
            "estan",
            "for",
            "from",
            "hay",
            "how",
            "in",
            "la",
            "las",
            "los",
            "me",
            "of",
            "para",
            "por",
            "que",
            "read",
            "se",
            "the",
            "this",
            "to",
            "tool",
            "un",
            "una",
            "use",
            "using",
            "what",
            "which",
            "y",
        }

        return [
            token
            for token in normalized.split()
            if (
                len(token) >= 2
                and token not in stopwords
            )
        ]


    def _select_relevant_tools(
        self,
        user_prompt: str,
        tools: list[dict],
    ) -> list[dict]:
        """
        Select relevant tools using declarative routing metadata.

        AIService contains no concrete tool names and no
        infrastructure-domain vocabulary.

        If routing confidence is insufficient, the complete catalog
        is returned and the normal LLM tool-calling path decides.
        """

        if not tools:
            return []

        prompt = (
            self._normalize_tool_routing_text(
                user_prompt
            )
        )

        if not prompt:
            return tools

        # ---------------------------------------------------------
        # Routing metadata is exposed by each OperatorTool.
        # ---------------------------------------------------------

        operator_tools = {
            tool.name: tool
            for tool in self.operator.list_tools()
        }

        scored = []

        for definition in tools:

            function = (
                definition.get(
                    "function",
                    {},
                )
                or {}
            )

            name = str(
                function.get(
                    "name",
                    "",
                )
                or ""
            )

            operator_tool = (
                operator_tools.get(
                    name
                )
            )

            hints = tuple(
                getattr(
                    operator_tool,
                    "routing_hints",
                    (),
                )
                or ()
            )

            # No explicit routing metadata:
            # do not guess using descriptions.
            if not hints:
                continue

            best_score = 0

            for hint in hints:

                normalized_hint = (
                    self._normalize_tool_routing_text(
                        hint
                    )
                )

                if not normalized_hint:
                    continue

                # -------------------------------------------------
                # Exact semantic phrase.
                # -------------------------------------------------

                if normalized_hint in prompt:

                    words = (
                        normalized_hint.split()
                    )

                    score = (
                        100
                        + len(words) * 10
                    )

                    best_score = max(
                        best_score,
                        score,
                    )

                    continue

                # -------------------------------------------------
                # Partial token match.
                #
                # Require meaningful overlap. This is intentionally
                # conservative so ambiguous requests fall back to the
                # full catalog.
                # -------------------------------------------------

                prompt_tokens = set(
                    self._tool_routing_tokens(
                        prompt
                    )
                )

                hint_tokens = set(
                    self._tool_routing_tokens(
                        normalized_hint
                    )
                )

                if not hint_tokens:
                    continue

                overlap = (
                    prompt_tokens
                    & hint_tokens
                )

                coverage = (
                    len(overlap)
                    / len(hint_tokens)
                )

                if (
                    len(overlap) >= 2
                    and coverage >= 0.60
                ):

                    score = int(
                        coverage * 50
                    )

                    best_score = max(
                        best_score,
                        score,
                    )

            if best_score > 0:

                scored.append(
                    (
                        best_score,
                        definition,
                    )
                )

        if not scored:
            return tools

        highest = max(
            score
            for score, _definition
            in scored
        )

        # ---------------------------------------------------------
        # Exact phrase matches dominate partial matches.
        # ---------------------------------------------------------

        if highest >= 100:

            selected = [
                definition
                for score, definition
                in scored
                if score == highest
            ]

        else:

            # Partial routing is intentionally conservative.
            candidates = [
                definition
                for score, definition
                in scored
                if score == highest
            ]

            if len(
                candidates
            ) != 1:
                return tools

            selected = candidates

        if not selected:
            return tools

        return selected


    def _execute_with_tools(
        self,
        provider,
        request,
        model,
    ):
        """
        Execute an LLM request with ATLAS tool calling.

        Instrumented for latency analysis.
        Behavior intentionally unchanged.
        """

        import time

        timing_total_start = time.perf_counter()

        tools = self._operator_tool_definitions()


        # ------------------------------------------------
        # GENERIC DECLARATIVE TOOL ROUTING
        # ------------------------------------------------

        original_tool_count = len(
            tools
        )

        user_prompt = (
            request.user_prompt
            if isinstance(
                request.user_prompt,
                str,
            )
            else ""
        )

        prompt_lower = (
            user_prompt.lower()
        )

        # OperatorAgent prompts need access to the complete tool set
        # because the model must return the strict agent JSON contract.
        agent_protocol_prompt = (
            "json" in prompt_lower
            and "action" in prompt_lower
            and "tool" in prompt_lower
            and "final" in prompt_lower
        )

        if not agent_protocol_prompt:

            selected_tools = (
                self._select_relevant_tools(
                    user_prompt,
                    tools,
                )
            )

            if (
                selected_tools
                and len(
                    selected_tools
                ) < len(
                    tools
                )
            ):

                tools = (
                    selected_tools
                )

                print(
                    "[AI TOOL ROUTING] "
                    f"selected={len(tools)} "
                    f"from={original_tool_count} "
                    "tools="
                    + ", ".join(
                        str(
                            tool.get(
                                "function",
                                {},
                            ).get(
                                "name",
                                "",
                            )
                        )
                        for tool in tools
                    )
                )

        tool_catalog_reduced = (
            len(tools)
            < original_tool_count
        )


        if (
            not tools
            or not hasattr(
                provider,
                "generate_with_tools",
            )
        ):
            timing_generate_start = time.perf_counter()

            result = provider.generate(
                request.user_prompt,
                model=model.provider_model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                # Keep the selected model loaded across tool-calling rounds.
                # This avoids reloading the Ollama model between ROUND 1 and ROUND 2.
                keep_alive=0,
            )

            timing_generate = (
                time.perf_counter()
                - timing_generate_start
            )

            timing_total = (
                time.perf_counter()
                - timing_total_start
            )

            print(
                f"[AI TIMING] generate={timing_generate:.2f}s "
                f"total={timing_total:.2f}s"
            )

            return result, []

        # ------------------------------------------------------------
        # CURRENT OPERATIONAL CONTEXT
        #
        # Build the live operational context through the internal
        # AIContextBuilder. This keeps infrastructure knowledge inside
        # the ATLAS runtime instead of relying on generated context
        # files or external snapshots.
        # ------------------------------------------------------------

        context_start = time.perf_counter()

        if tool_catalog_reduced:

            # A high-confidence routing decision means the live tool
            # is the authoritative source for this request.
            #
            # Do not build/send the complete ATLAS operational
            # context for a narrow telemetry query.
            ai_context_text = "{}"

            print(
                "[AI CONTEXT] "
                "skipped=tool_routing "
                f"tools={len(tools)}"
            )

        else:

            try:

                ai_context = (
                    self.context_builder.build()
                )

                ai_context_text = json.dumps(
                    ai_context,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    default=str,
                )

                print(
                    "[AI CONTEXT] "
                    f"built="
                    f"{time.perf_counter() - context_start:.2f}s "
                    f"chars={len(ai_context_text)}"
                )

            except Exception as exc:

                ai_context_text = json.dumps(
                    {
                        "_context_error":
                            str(exc),
                    },
                    ensure_ascii=False,
                )

                print(
                    "[AI CONTEXT] ERROR "
                    f"{exc}"
                )


        messages = [
            {
                "role": "system",
                "content": (
                    "You are ATLAS, an infrastructure operations assistant.\n\n"

                    "The following JSON is the CURRENT OPERATIONAL STATE "
                    "of the infrastructure. Treat it as authoritative "
                    "for current infrastructure facts unless a live "
                    "telemetry tool provides newer information.\n\n"

                    "IMPORTANT: reason over the complete context. "
                    "Do not require a dedicated tool merely because "
                    "the user asks a differently worded question. "
                    "Resolve entities, storage devices, filesystems, "
                    "applications, containers, hosts and relationships "
                    "from the JSON whenever the required information "
                    "is already present.\n\n"

                    "Never invent values that are absent from the context. "
                    "If a requested value is not present, explicitly say "
                    "that it is unavailable.\n\n"

                    "CURRENT ATLAS CONTEXT:\n"
                    + ai_context_text
                ),
            },
            {
                "role": "user",
                "content": request.user_prompt,
            }
        ]

        tool_history = []

        max_tool_rounds = 5

        for round_number in range(
            max_tool_rounds
        ):

            round_start = time.perf_counter()

            print(
                f"[AI TIMING] ROUND {round_number + 1} START"
            )

            generate_start = time.perf_counter()

            print(
                f"[AI CONTEXT] round={round_number + 1} "
                f"messages={len(messages)} "
                f"chars={sum(len(str(m.get('content', ''))) for m in messages)}"
            )

            for _i, _m in enumerate(messages):
                _content = str(_m.get("content", ""))
                print(
                    f"[AI CONTEXT DETAIL] "
                    f"i={_i} "
                    f"role={_m.get('role')} "
                    f"chars={len(_content)} "
                    f"tool_name={_m.get('tool_name', '')}"
                )

            response = provider.generate_with_tools(
                messages,
                tools,
                model=model.provider_model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                # Keep the SAME model resident only during the
                # current tool-calling execution.
                #
                # The model is explicitly unloaded when the execution
                # finishes, so another model cannot remain resident.
                keep_alive=0,
            )

            generate_elapsed = (
                time.perf_counter()
                - generate_start
            )

            message = (
                response.get(
                    "message",
                    {},
                )
                if isinstance(
                    response,
                    dict,
                )
                else {}
            )

            tool_calls = (
                message.get(
                    "tool_calls",
                    [],
                )
                or []
            )

            content = (
                message.get(
                    "content",
                    "",
                )
                or ""
            )

            print(
                f"[AI TIMING] ROUND {round_number + 1} "
                f"generate={generate_elapsed:.2f}s "
                f"tool_calls={len(tool_calls)}"
            )

            # ------------------------------------------------
            # Normal assistant response.
            # ------------------------------------------------

            if not tool_calls:

                total_elapsed = (
                    time.perf_counter()
                    - timing_total_start
                )

                print(
                    f"[AI TIMING] COMPLETE "
                    f"rounds={round_number + 1} "
                    f"total={total_elapsed:.2f}s"
                )

                return (
                    content,
                    tool_history,
                )

            # ------------------------------------------------
            # Assistant requested tools.
            # ------------------------------------------------

            messages.append(
                message
            )

            tools_start = time.perf_counter()

            results = (
                self._execute_operator_tool_calls(
                    tool_calls
                )
            )

            tools_elapsed = (
                time.perf_counter()
                - tools_start
            )

            print(
                f"[AI TIMING] ROUND {round_number + 1} "
                f"tools={tools_elapsed:.3f}s"
            )

            # ------------------------------------------------
            # Store complete tool results.
            #
            # The tools already returned verified telemetry.
            # Do not force another LLM inference merely to
            # rephrase deterministic infrastructure values.
            # ------------------------------------------------

            for item in results:

                tool_history.append(
                    item
                )

            # ------------------------------------------------
            # Fast deterministic synthesis.
            #
            # If the executed tools provide the exact values
            # requested by the user, answer directly from the
            # verified telemetry.
            #
            # This removes the expensive ROUND 2 Ollama call.
            # ------------------------------------------------
            # Generic deterministic synthesis.
            # ------------------------------------------------

            content = synthesize_verified_tool_results(
                request.user_prompt,
                results,
            )

            if content is not None:

                total_elapsed = (
                    time.perf_counter()
                    - timing_total_start
                )

                print(
                    "[AI TIMING] FAST SYNTHESIS "
                    f"total={total_elapsed:.2f}s"
                )

                return (
                    content,
                    tool_history,
                )


            # ------------------------------------------------
            # Generic fallback.
            #
            # If the executed tools do not match a deterministic
            # synthesis path, continue with the normal LLM
            # synthesis flow.
            # ------------------------------------------------

            compact_results = []

            for item in results:

                tool_name = item.get(
                    "name"
                )

                tool_result = item.get(
                    "result",
                    {},
                )

                llm_tool_result = (
                    self._compact_tool_result(
                        tool_name,
                        tool_result,
                    )
                )

                compact_results.append(
                    {
                        "tool": tool_name,
                        "result": llm_tool_result,
                    }
                )

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are ATLAS, an infrastructure operations assistant. "
                        "Answer the user's question using only the verified "
                        "telemetry below. Do not call tools. "
                        "Do not invent values. Be concise."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Question: "
                        + request.user_prompt
                        + "\n\n"
                        + "Verified telemetry:\n"
                        + json.dumps(
                            compact_results,
                            ensure_ascii=False,
                        )
                    ),
                },
            ]

            round_elapsed = (
                time.perf_counter()
                - round_start
            )

            print(
                f"[AI TIMING] ROUND {round_number + 1} "
                f"total={round_elapsed:.2f}s"
            )

        total_elapsed = (
            time.perf_counter()
            - timing_total_start
        )

        print(
            f"[AI TIMING] STOPPED "
            f"rounds={max_tool_rounds} "
            f"total={total_elapsed:.2f}s"
        )

        return (
            "Tool execution stopped after "
            f"{max_tool_rounds} rounds.",
            tool_history,
        )


    def deterministic_tool_query(
        self,
        user_prompt: str,
    ) -> dict | None:
        """
        Execute a single high-confidence parameterless tool without
        invoking an LLM.

        Tool selection and synthesis are both declarative. This method
        contains no knowledge of concrete infrastructure tools.
        """

        if not isinstance(
            user_prompt,
            str,
        ):
            return None

        if not user_prompt.strip():
            return None

        tools = (
            self._operator_tool_definitions()
        )

        if not tools:
            return None

        selected = (
            self._select_relevant_tools(
                user_prompt,
                tools,
            )
        )

        # No confident reduction.
        if (
            not selected
            or len(selected) != 1
            or len(selected) >= len(tools)
        ):
            return None

        function = (
            selected[0].get(
                "function",
                {},
            )
            or {}
        )

        tool_name = (
            function.get(
                "name"
            )
        )

        if not tool_name:
            return None

        parameters = (
            function.get(
                "parameters",
                {},
            )
            or {}
        )

        required = (
            parameters.get(
                "required",
                []
            )
            or []
        )

        # Never guess required tool arguments.
        if required:
            return None

        if not can_synthesize_tool(
            tool_name
        ):
            return None

        results = (
            self._execute_routed_tools(
                [
                    tool_name,
                ]
            )
        )

        content = (
            synthesize_verified_tool_results(
                user_prompt,
                results,
            )
        )

        if content is None:
            return None

        return {
            "content":
                content,
            "results":
                results,
            "tools": [
                tool_name,
            ],
        }


    def _execute_with_model(
        self,
        request: AIRequest,
        model,
    ) -> LLMResponse:

        # ============================================================
        # DETERMINISTIC SEMANTIC PREFLIGHT
        #
        # Resolve read-only infrastructure questions before touching
        # the selected LLM provider, loading a model or building the
        # complete tool catalog.
        #
        # OperatorAgent protocol prompts are intentionally excluded:
        # they require the strict JSON agent contract.
        # ============================================================

        user_prompt = (
            request.user_prompt
            if isinstance(
                request.user_prompt,
                str,
            )
            else ""
        )

        prompt_lower = (
            user_prompt.lower()
        )

        agent_protocol_prompt = (
            "json" in prompt_lower
            and "action" in prompt_lower
            and "tool" in prompt_lower
            and "final" in prompt_lower
        )

        if not agent_protocol_prompt:

            semantic_start = (
                time.perf_counter()
            )

            semantic_result = (
                self.deterministic_semantic_query(
                    user_prompt
                )
            )

            if semantic_result is not None:

                content = (
                    self.synthesize_semantic_result(
                        semantic_result
                    )
                )

                latency_ms = (
                    time.perf_counter()
                    - semantic_start
                ) * 1000

                semantic = (
                    semantic_result.get(
                        "semantic"
                    )
                    or {}
                )

                print(
                    "[AI SEMANTIC DIRECT] "
                    f"intent={semantic.get('intent')} "
                    f"latency={latency_ms:.2f}ms"
                )

                return LLMResponse(
                    model="atlas-semantic",
                    provider="atlas",
                    content=content,
                    latency_ms=round(
                        latency_ms,
                        2,
                    ),
                    metadata={
                        "deterministic":
                            True,
                        "semantic":
                            semantic,
                        "tools_used": [
                            "semantic_query",
                        ],
                        "llm_used":
                            False,
                        "selected_model":
                            getattr(
                                model,
                                "name",
                                None,
                            ),
                    },
                )

        # ============================================================
        # DETERMINISTIC TOOL PREFLIGHT
        #
        # High-confidence parameterless telemetry tools can execute
        # directly before touching the LLM provider.
        # ============================================================

        if not agent_protocol_prompt:

            tool_start = (
                time.perf_counter()
            )

            tool_result = (
                self.deterministic_tool_query(
                    user_prompt
                )
            )

            if tool_result is not None:

                latency_ms = (
                    time.perf_counter()
                    - tool_start
                ) * 1000

                tools_used = (
                    tool_result.get(
                        "tools",
                        [],
                    )
                )

                print(
                    "[AI TOOL DIRECT] "
                    f"tools={','.join(tools_used)} "
                    f"latency={latency_ms:.2f}ms"
                )

                return LLMResponse(
                    model="atlas-tools",
                    provider="atlas",
                    content=tool_result[
                        "content"
                    ],
                    latency_ms=round(
                        latency_ms,
                        2,
                    ),
                    metadata={
                        "deterministic":
                            True,
                        "tools_used":
                            tools_used,
                        "llm_used":
                            False,
                    },
                )


        provider = self.providers.get(
            model.provider
        )

        # ============================================================
        # MINIMAL KNOWLEDGE-AGENT PROTOCOL
        #
        # OperatorAgent owns tool selection and execution through MCP.
        # The nested planner request therefore needs ONLY its small
        # protocol prompt. Do not attach the complete ATLAS context and
        # do not expose the internal native ToolRegistry to the model.
        # ============================================================

        if (
            agent_protocol_prompt
            and request.context_required is False
            and provider is not None
        ):

            agent_start = (
                time.perf_counter()
            )

            print(
                "[AI AGENT PROTOCOL] "
                "context=skipped "
                "native_tools=0"
            )

            result = provider.generate(
                request.user_prompt,
                model=model.provider_model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                keep_alive=0,
            )

            latency_ms = (
                time.perf_counter()
                - agent_start
            ) * 1000

            return LLMResponse(
                model=model.name,
                provider=model.provider,
                content=result,
                latency_ms=round(
                    latency_ms,
                    2,
                ),
                metadata={
                    "agent_protocol":
                        True,

                    "minimal_context":
                        True,

                    "tools_used":
                        [],

                    "llm_used":
                        True,
                },
            )

        if not provider:

            return LLMResponse(

                model=model.name,

                provider=model.provider,

                content="Provider unavailable",

            )


        # ----------------------------------------------------
        # Execute primary.
        # ----------------------------------------------------

        gate_result = None

        # Track fallback candidates so the physical provider models
        # can be unloaded in the final cleanup boundary.
        fallbacks = []

        try:

            if not provider.available():

                self.runtime.record_failure(
                    model.name,
                    "LLM unavailable",
                )

                raise RuntimeError(
                    "LLM unavailable"
                )


            self.runtime.load(
                model.name
            )

            self.runtime.record_request(
                model.name
            )

            start = time.perf_counter()

            result, tool_history = (
                self._execute_with_tools(
                    provider,
                    request,
                    model,
                )
            )

            latency = (
                time.perf_counter()
                - start
            ) * 1000

            if not result or not result.strip():

                raise RuntimeError(
                    "Primary model returned empty response"
                )

            # ------------------------------------------------
            # Reasoning quality gate.
            #
            # A successful LLM request is not necessarily a
            # successful reasoning result. For reasoning tasks
            # the gate validates confidence, evidence, missing
            # evidence and root cause before accepting the model.
            # ------------------------------------------------

            gate_result = self.reasoning_gate.evaluate(
                result,
                task=request.task,
            )

            if gate_result.escalate:

                raise RuntimeError(
                    "Reasoning gate escalation: "
                    + ", ".join(
                        gate_result.reasons
                    )
                )

            self.runtime.record_success(
                model.name,
                round(latency, 2),
            )

            return LLMResponse(

                model=model.name,

                provider=model.provider,

                content=result,

                latency_ms=round(
                    latency,
                    2,
                ),

                metadata={
                    "fallback": False,
                    "primary_model": model.name,
                    "tools_used": [
                        item["name"]
                        for item in tool_history
                    ],
                    "tool_calls": tool_history,
                },

            )


        except Exception as exc:

            self.runtime.record_failure(
                model.name,
                str(exc),
            )


            # ------------------------------------------------
            # IMPORTANT:
            # Make sure the 7B is considered unloaded before
            # attempting the 14B fallback.
            # ------------------------------------------------

            # IMPORTANT:
            # runtime.unload() only changes ATLAS state.
            # _unload_model() also forces the physical provider
            # (Ollama) to release the model with keep_alive=0.
            self._unload_model(
                model
            )


            fallbacks = self.operator.fallback_candidates(
                model,
                self.runtime,
            )


            # No fallback available.
            if not fallbacks:

                return LLMResponse(

                    model=model.name,

                    provider=model.provider,

                    content=(
                        "Primary AI model failed and "
                        "no fallback model is available."
                    ),

                    metadata={

                        "fallback": False,

                        "primary_model":
                            model.name,

                        "error":
                            str(exc),

                    },

                )


            # ------------------------------------------------
            # Fallback chain.
            # ------------------------------------------------

            for fallback in fallbacks:

                try:

                    self.runtime.load(
                        fallback.name
                    )

                    self.runtime.record_request(
                        fallback.name
                    )

                    start = time.perf_counter()

                    fallback_result, fallback_tool_history = (
                        self._execute_with_tools(
                            provider,
                            request,
                            fallback,
                        )
                    )

                    latency = (
                        time.perf_counter()
                        - start
                    ) * 1000


                    if (
                        not fallback_result
                        or not fallback_result.strip()
                    ):

                        raise RuntimeError(
                            "Fallback model returned empty response"
                        )

                    # ------------------------------------------------
                    # Reasoning quality gate for fallback responses.
                    #
                    # A fallback model must satisfy the same reasoning
                    # contract as the primary model before ATLAS accepts
                    # its result.
                    # ------------------------------------------------

                    fallback_gate_result = (
                        self.reasoning_gate.evaluate(
                            fallback_result,
                            task=request.task,
                        )
                    )

                    if fallback_gate_result.escalate:

                        raise RuntimeError(
                            "Fallback reasoning gate escalation: "
                            + ", ".join(
                                fallback_gate_result.reasons
                            )
                        )


                    self.runtime.record_success(
                        fallback.name,
                        round(latency, 2),
                    )


                    return LLMResponse(

                        model=fallback.name,

                        provider=fallback.provider,

                        content=fallback_result,

                        latency_ms=round(
                            latency,
                            2,
                        ),

                        metadata={

                            "fallback": True,

                            "primary_model":
                                model.name,

                            "fallback_model":
                                fallback.name,

                            "fallback_reason":
                                (
                                    "reasoning_gate"
                                    if gate_result is not None
                                    else str(exc)
                                ),

                            "tools_used": [
                                item["name"]
                                for item in fallback_tool_history
                            ],

                            "tool_calls": fallback_tool_history,

                            "reasoning_gate": (
                                {
                                    "escalate":
                                        getattr(
                                            gate_result,
                                            "escalate",
                                            False,
                                        ),
                                    "score":
                                        getattr(
                                            gate_result,
                                            "score",
                                            None,
                                        ),
                                    "reasons":
                                        getattr(
                                            gate_result,
                                            "reasons",
                                            [],
                                        ),
                                }
                                if gate_result is not None
                                else None
                            ),

                        },

                    )


                except Exception as fallback_exc:

                    self.runtime.record_failure(
                        fallback.name,
                        str(fallback_exc),
                    )

                    # Physically unload the fallback model as well.
                    self._unload_model(
                        fallback
                    )

                    continue


            return LLMResponse(

                model=model.name,

                provider=model.provider,

                content=(
                    "Primary AI model failed and "
                    "all fallback models failed."
                ),

                metadata={

                    "fallback": True,

                    "primary_model":
                        model.name,

                    "error":
                        str(exc),

                    "fallbacks_attempted": [
                        item.name
                        for item in fallbacks
                    ],

                },

            )


        finally:

            # ------------------------------------------------
            # HARD PHYSICAL MEMORY BOUNDARY
            #
            # runtime.unload_all() only clears ATLAS bookkeeping.
            # The provider must also be explicitly instructed to
            # unload every model that may have participated in this
            # execution.
            #
            # This guarantees that a primary 7B model cannot remain
            # resident while a fallback 14B model is loaded, and that
            # no model remains resident after execution completes.
            # ------------------------------------------------

            cleanup_models = [
                model,
                *fallbacks,
            ]

            seen_models = set()

            for cleanup_model in cleanup_models:

                if cleanup_model is None:
                    continue

                model_key = (
                    getattr(
                        cleanup_model,
                        "provider",
                        None,
                    ),
                    getattr(
                        cleanup_model,
                        "provider_model",
                        None,
                    ),
                    getattr(
                        cleanup_model,
                        "name",
                        None,
                    ),
                )

                if model_key in seen_models:
                    continue

                seen_models.add(
                    model_key
                )

                try:
                    self._unload_model(
                        cleanup_model
                    )
                except Exception as cleanup_exc:
                    print(
                        "[AI CLEANUP] "
                        f"failed to unload "
                        f"{model_key}: "
                        f"{cleanup_exc}"
                    )

            # Always synchronize ATLAS runtime state as the final step.
            self.runtime.unload_all()



    def analyze_root_cause(self):

        context = self.context_builder.build()

        prompt = self.prompt_builder.build_root_cause(
            context
        )

        request = AIRequest(

            task="root_cause",

            user_prompt=prompt,

        )

        return self.ask(
            request
        )



    def _govern_reasoning_confidence(
        self,
        parsed,
        incident_data,
    ):
        """
        Apply deterministic ATLAS governance to LLM confidence.

        The LLM may propose a root-cause hypothesis, but ATLAS
        prevents unsupported confidence from becoming operational
        truth.
        """

        if not isinstance(
            parsed,
            dict,
        ):
            return parsed

        evidence = incident_data.get(
            "evidence",
            [],
        )

        if not isinstance(
            evidence,
            list,
        ):
            evidence = (
                [str(evidence)]
                if evidence
                else []
            )

        missing = parsed.get(
            "missing_evidence",
            [],
        )

        if not isinstance(
            missing,
            list,
        ):
            missing = (
                [str(missing)]
                if missing
                else []
            )

        root_cause = str(
            parsed.get(
                "root_cause",
                "",
            )
        ).strip()

        try:
            model_confidence = float(
                parsed.get(
                    "confidence",
                    0.0,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            model_confidence = 0.0

        model_confidence = max(
            0.0,
            min(
                1.0,
                model_confidence,
            ),
        )

        observed_evidence = {
            str(item).strip().lower()
            for item in evidence
            if str(item).strip()
        }

        #
        # No deterministic evidence means the model cannot
        # retain high confidence.
        #
        if not observed_evidence:
            parsed["confidence"] = min(
                model_confidence,
                0.2,
            )

            if (
                "Direct incident evidence"
                not in missing
            ):
                missing.append(
                    "Direct incident evidence"
                )

            parsed["missing_evidence"] = missing

            return parsed

        #
        # Configuration/root-cause hypotheses require explicit
        # configuration evidence.
        #
        root_lower = root_cause.lower()

        hypothesis_markers = (
            "misconfig",
            "incorrect",
            "wrong",
            "invalid",
            "failure of",
            "failed configuration",
            "configuration issue",
            "configuration error",
            "resolver configuration",
            "network configuration",
            "dns configuration",
            "docker configuration",
            "host configuration",
        )

        configuration_hypothesis = any(
            marker in root_lower
            for marker in hypothesis_markers
        )

        if configuration_hypothesis:

            configuration_evidence = any(
                any(
                    token in item
                    for token in (
                        "config",
                        "configured",
                        "configuration",
                        "nameserver",
                        "dns server",
                        "network settings",
                    )
                )
                for item in observed_evidence
            )

            if not configuration_evidence:

                model_confidence = min(
                    model_confidence,
                    0.6,
                )

                for item in (
                    "Docker network configuration",
                    "Container DNS configuration",
                    "Host resolver configuration",
                ):
                    if item not in missing:
                        missing.append(item)

        #
        # Missing evidence creates an unresolved-alternatives
        # ceiling.
        #
        if missing:
            model_confidence = min(
                model_confidence,
                0.6,
            )

        parsed["confidence"] = max(
            0.0,
            min(
                1.0,
                model_confidence,
            ),
        )

        parsed["missing_evidence"] = missing

        return parsed


    def analyze_incident_reasoning(
        self,
        incident,
    ):
        # --------------------------------------------------------
        # Normalize incident input.
        #
        # Supported inputs:
        #   1. dict
        #   2. dataclass / object with __dict__
        #   3. generic object
        # --------------------------------------------------------

        if isinstance(incident, dict):

            incident_data = dict(
                incident
            )

        elif hasattr(
            incident,
            "__dict__",
        ):

            incident_data = dict(
                incident.__dict__
            )

        else:

            incident_data = {
                "incident_id": getattr(
                    incident,
                    "incident_id",
                    "",
                ),

                "id": getattr(
                    incident,
                    "id",
                    "",
                ),

                "name": getattr(
                    incident,
                    "name",
                    "",
                ),

                "asset": getattr(
                    incident,
                    "asset",
                    "",
                ),

                "severity": getattr(
                    incident,
                    "severity",
                    "",
                ),

                "incident_score": getattr(
                    incident,
                    "incident_score",
                    0,
                ),

                "root_cause": getattr(
                    incident,
                    "root_cause",
                    "",
                ),

                "diagnosis": getattr(
                    incident,
                    "diagnosis",
                    "",
                ),

                "affected_assets": getattr(
                    incident,
                    "affected_assets",
                    [],
                ),

                "impact": getattr(
                    incident,
                    "impact",
                    [],
                ),

                "blast_radius": getattr(
                    incident,
                    "blast_radius",
                    [],
                ),

                "evidence": getattr(
                    incident,
                    "evidence",
                    [],
                ),

                "recommendation": getattr(
                    incident,
                    "recommendation",
                    {},
                ),

                "memory_intelligence": getattr(
                    incident,
                    "memory_intelligence",
                    {},
                ),
            }

        # --------------------------------------------------------
        # Resolve persistent incident identity.
        # --------------------------------------------------------

        incident_id = (
            incident_data.get("incident_id")
            or incident_data.get("id")
        )

        if not incident_id:
            incident_id = (
                getattr(
                    incident,
                    "incident_id",
                    None,
                )
                or getattr(
                    incident,
                    "id",
                    None,
                )
            )

        # --------------------------------------------------------
        # Build canonical operational context.
        # --------------------------------------------------------

        operational_context = {}

        #
        # Persistent incident identity is authoritative.
        #
        # `id`          = internal NOC UUID
        # `incident_id` = persistent IncidentManager identity
        #
        # AI reasoning must operate on the persistent identity.
        #

        if not incident_id:
            incident_id = (
                incident_data.get("id")
                or incident_data.get("incident_id")
            )

        if incident_id:
            try:
                context = (
                    self.context_builder.build_for_incident(
                        incident_id
                    )
                )

                if hasattr(
                    context,
                    "to_dict",
                ):
                    operational_context = (
                        context.to_dict()
                    )
                elif isinstance(
                    context,
                    dict,
                ):
                    operational_context = context

            except Exception as exc:
                operational_context = {
                    "_context_error": str(exc)
                }

        # --------------------------------------------------------
        # Explicit evidence domains.
        # --------------------------------------------------------

        reasoning_context = dict(
            incident_data
        )

        #
        # Explicit identity boundary for the experimental AI.
        #
        reasoning_context[
            "_operational_identity"
        ] = {
            "incident_id": incident_id,
            "internal_id": incident_data.get(
                "id",
                "",
            ),
        }

        # --------------------------------------------------------
        # Keep incident evidence separate from derived context.
        #
        # The model must never confuse infrastructure context
        # with observations belonging to the incident.
        # --------------------------------------------------------

        reasoning_context[
            "_operational_infrastructure"
        ] = operational_context.get(
            "infrastructure",
            {},
        )

        reasoning_context[
            "_operational_assets"
        ] = operational_context.get(
            "assets",
            {},
        )

        reasoning_context[
            "_operational_topology"
        ] = operational_context.get(
            "topology",
            {},
        )

        reasoning_context[
            "_operational_health"
        ] = operational_context.get(
            "health",
            {},
        )

        reasoning_context[
            "_operational_events"
        ] = operational_context.get(
            "events",
            {},
        )

        reasoning_context[
            "_operational_lifecycle"
        ] = operational_context.get(
            "operational_state",
            operational_context.get(
                "lifecycle",
                {},
            ),
        )

        reasoning_context[
            "_operational_knowledge"
        ] = operational_context.get(
            "knowledge",
            {},
        )

        reasoning_context[
            "_operational_history"
        ] = operational_context.get(
            "history",
            [],
        )

        reasoning_context[
            "_operational_learning"
        ] = operational_context.get(
            "learning",
            [],
        )

        prompt = (
            self.prompt_builder.build_incident_reasoning(
                reasoning_context
            )
        )

        request = AIRequest(
            task="incident_reasoning",
            user_prompt=prompt,
        )

        response = self.ask(
            request
        )

        raw_content = response.content

        parsed = self._parse_reasoning_response(
            raw_content
        )

        # --------------------------------------------------------
        # Normalize model output.
        # --------------------------------------------------------

        root_cause = parsed.get(
            "root_cause"
        )

        if isinstance(
            root_cause,
            list,
        ):
            parsed["root_cause"] = (
                str(root_cause[0])
                if root_cause
                else "Insufficient evidence"
            )

        elif root_cause is None:
            parsed["root_cause"] = (
                "Insufficient evidence"
            )

        for field in (
            "evidence",
            "impact",
            "missing_evidence",
        ):
            value = parsed.get(field)

            if isinstance(
                value,
                list,
            ):
                continue

            if value:
                parsed[field] = [
                    str(value)
                ]
            else:
                parsed[field] = []

        confidence = parsed.get(
            "confidence",
            0.0,
        )

        try:
            confidence = float(
                confidence
            )
        except (
            TypeError,
            ValueError,
        ):
            confidence = 0.0

        parsed["confidence"] = max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )

        #
        # Experimental AI traceability.
        #
        # The parser may return a response without metadata.
        # Always initialize the metadata container before
        # adding ATLAS execution information.
        #

        metadata = parsed.get(
            "_metadata",
            {},
        )

        if not isinstance(
            metadata,
            dict,
        ):
            metadata = {}

        metadata["experimental_ai"] = True
        metadata["identity"] = incident_id

        parsed["_metadata"] = metadata

        # --------------------------------------------------------
        # ATLAS reasoning governance.
        #
        # The LLM proposes a diagnosis.
        # ATLAS decides whether the confidence is justified by
        # deterministic incident evidence.
        # --------------------------------------------------------

        parsed = self._govern_reasoning_confidence(
            parsed,
            incident_data,
        )

        parsed["_metadata"] = {
            "model": response.model,
            "provider": response.provider,
            "latency_ms": response.latency_ms,
            "incident_id": incident_id,
        }

        # --------------------------------------------------------
        # Persist structured reasoning.
        # --------------------------------------------------------

        if hasattr(
            incident,
            "ai_analysis",
        ):
            incident.ai_analysis = dict(
                parsed
            )

        #
        # Keep the NOCIncident AI projection synchronized with
        # the authoritative structured reasoning result.
        #
        if hasattr(
            incident,
            "ai_confidence",
        ):
            incident.ai_confidence = float(
                parsed.get(
                    "confidence",
                    0.0,
                )
            )

        if hasattr(
            incident,
            "ai_reasoning",
        ):
            incident.ai_reasoning = [
                {
                    "type": "root_cause",
                    "content": parsed.get(
                        "root_cause",
                        "",
                    ),
                },
                *[
                    {
                        "type": "evidence",
                        "content": item,
                    }
                    for item in parsed.get(
                        "evidence",
                        [],
                    )
                ],
                *[
                    {
                        "type": "impact",
                        "content": item,
                    }
                    for item in parsed.get(
                        "impact",
                        [],
                    )
                ],
            ]

        if hasattr(
            incident,
            "ai_recommendation",
        ):
            incident.ai_recommendation = (
                parsed.get(
                    "recommendation",
                    "",
                )
            )

        return parsed


    @staticmethod
    def _parse_reasoning_response(
        raw_content: str,
    ) -> dict:
        """
        Normalize experimental LLM reasoning output.

        Qwen may occasionally return:
        - plain JSON
        - Markdown fenced JSON
        - JSON wrapped inside an "analysis" object
        - additional text around the JSON

        ATLAS normalizes all of these into the internal
        reasoning contract.
        """

        fallback = {
            "summary": raw_content,
            "root_cause": "",
            "evidence": [],
            "impact": [],
            "risk": "UNKNOWN",
            "recommendation": "",
            "missing_evidence": [],
            "confidence": 0.0,
            "parse_error": True,
        }

        if not isinstance(
            raw_content,
            str,
        ):
            return fallback

        content = raw_content.strip()

        if not content:
            return fallback

        # ----------------------------------------------------
        # Remove Markdown code fences.
        # ----------------------------------------------------

        if content.startswith("```"):

            lines = content.splitlines()

            if lines:

                lines = lines[1:]

            if lines and lines[-1].strip() == "```":

                lines = lines[:-1]

            content = "\n".join(
                lines
            ).strip()

        # ----------------------------------------------------
        # First JSON attempt.
        # ----------------------------------------------------

        try:

            parsed = json.loads(
                content
            )

        except (
            json.JSONDecodeError,
            TypeError,
        ):

            parsed = None

        # ----------------------------------------------------
        # JSON embedded inside surrounding text.
        # ----------------------------------------------------

        if parsed is None:

            start = content.find("{")
            end = content.rfind("}")

            if (
                start >= 0
                and end > start
            ):

                candidate = content[
                    start:end + 1
                ]

                try:

                    parsed = json.loads(
                        candidate
                    )

                except (
                    json.JSONDecodeError,
                    TypeError,
                ):

                    parsed = None

        if not isinstance(
            parsed,
            dict,
        ):

            return fallback

        # ----------------------------------------------------
        # Qwen sometimes wraps the actual answer in:
        #
        # {
        #   "analysis": {
        #       ...
        #   }
        # }
        # ----------------------------------------------------

        if isinstance(
            parsed.get("analysis"),
            dict,
        ):

            nested = parsed["analysis"]

            # Preserve useful wrapper fields if present.
            if "summary" not in nested:
                nested["summary"] = parsed.get(
                    "summary",
                    "",
                )

            parsed = nested

        # ----------------------------------------------------
        # Normalize fields.
        # ----------------------------------------------------

        result = {
            "summary": parsed.get(
                "summary",
                "",
            ),

            "root_cause": parsed.get(
                "root_cause",
                parsed.get(
                    "likely_root_cause",
                    "",
                ),
            ),

            "evidence": parsed.get(
                "evidence",
                parsed.get(
                    "evidence_supporting_it",
                    [],
                ),
            ),

            "impact": parsed.get(
                "impact",
                [],
            ),

            "risk": parsed.get(
                "risk",
                "UNKNOWN",
            ),

            "recommendation": parsed.get(
                "recommendation",
                parsed.get(
                    "safest_next_diagnostic_action",
                    "",
                ),
            ),

            "missing_evidence": parsed.get(
                "missing_evidence",
                [],
            ),

            "confidence": parsed.get(
                "confidence",
                0.0,
            ),

            "parse_error": False,
        }

        # ----------------------------------------------------
        # Normalize collection types.
        # ----------------------------------------------------

        for key in (
            "evidence",
            "impact",
            "missing_evidence",
        ):

            value = result[key]

            if value is None:

                result[key] = []

            elif isinstance(
                value,
                str,
            ):

                result[key] = [
                    value
                ]

            elif not isinstance(
                value,
                list,
            ):

                result[key] = [
                    str(value)
                ]

        # ----------------------------------------------------
        # Normalize confidence.
        # ----------------------------------------------------

        try:

            confidence = float(
                result["confidence"]
            )

        except (
            TypeError,
            ValueError,
        ):

            confidence = 0.0

        result["confidence"] = max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )

        # ----------------------------------------------------
        # Normalize risk.
        # ----------------------------------------------------

        risk = str(
            result.get(
                "risk",
                "UNKNOWN",
            )
        ).upper()

        allowed_risks = {
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL",
            "UNKNOWN",
        }

        if risk not in allowed_risks:

            risk = "UNKNOWN"

        result["risk"] = risk

        return result


    def generate_summary(self):

        context = self.context_builder.build()

        prompt = self.prompt_builder.build_summary(
            context
        )

        request = AIRequest(

            task="summary",

            user_prompt=prompt,

        )

        return self.ask(
            request
        )



    def coding_assistant(
        self,
        request_text: str,
    ):

        prompt = self.prompt_builder.build_coding(
            request_text
        )

        request = AIRequest(

            task="coding",

            user_prompt=prompt,

        )

        return self.ask(
            request
        )
