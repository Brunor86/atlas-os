from types import SimpleNamespace

from atlas.services.ai.models import (
    AIRequest,
)

from atlas.services.ai.semantic.planning import (
    InventoryQueryPlan,
)

from atlas.services.ai.service import (
    AIService,
)


class FakeRuntime:

    def __init__(
        self,
    ):

        self.events = []


    def load(
        self,
        model,
    ):

        self.events.append(
            (
                "load",
                model,
            )
        )


    def record_request(
        self,
        model,
    ):

        self.events.append(
            (
                "request",
                model,
            )
        )


    def record_success(
        self,
        model,
        *args,
    ):

        self.events.append(
            (
                "success",
                model,
            )
        )


    def record_failure(
        self,
        model,
        *args,
    ):

        self.events.append(
            (
                "failure",
                model,
            )
        )


    def unload_all(
        self,
    ):

        self.events.append(
            (
                "unload_all",
            )
        )


def build_service():

    service = AIService.__new__(
        AIService
    )

    service.runtime = (
        FakeRuntime()
    )

    service.runtime_target = (
        SimpleNamespace(
            provider="ollama",
            url=(
                "ollama://"
                "127.0.0.1:11434"
            ),
        )
    )

    model = SimpleNamespace(
        name="synthetic-reasoning",
        provider="ollama",
        provider_model="synthetic:1b",
    )

    service._select_model_with_refresh = (
        lambda task:
            model
    )

    service._unload_model = (
        lambda selected:
            service.runtime.events.append(
                (
                    "unload",
                    selected.name,
                )
            )
    )

    return service


def test_planned_inventory_query_executes_typed_selectors(
    monkeypatch,
):

    import atlas.services.ai.semantic.pydantic_planner as planner_module
    import atlas.services.ai.service as service_module

    calls = {}


    class FakePlanner:

        @classmethod
        def for_ollama(
            cls,
            **kwargs,
        ):

            calls[
                "planner_config"
            ] = kwargs

            return cls()


        def plan(
            self,
            question,
        ):

            calls[
                "question"
            ] = question

            return InventoryQueryPlan(
                intent="INVENTORY",
                asset_types=[
                    "VM",
                ],
                statuses=[
                    "ONLINE",
                ],
                reason=(
                    "synthetic typed "
                    "inventory"
                ),
                confidence=0.95,
            )


    class FakeEngine:

        def query_inventory_selectors(
            self,
            *,
            question,
            asset_types,
            statuses,
        ):

            calls[
                "execution"
            ] = {
                "question":
                    question,

                "asset_types":
                    list(
                        asset_types
                    ),

                "statuses":
                    list(
                        statuses
                    ),
            }

            return {
                "status":
                    "SUCCESS",

                "count":
                    1,

                "assets": [
                    {
                        "id":
                            "vm-synthetic-alpha",

                        "name":
                            "synthetic-alpha",

                        "type":
                            "VM",

                        "status":
                            "ONLINE",
                    }
                ],

                "semantic": {
                    "intent":
                        "INVENTORY",

                    "asset_type":
                        "VM",

                    "asset_types": [
                        "VM",
                    ],

                    "status":
                        "ONLINE",

                    "statuses": [
                        "ONLINE",
                    ],
                },
            }


    monkeypatch.setattr(
        planner_module,
        "PydanticInventoryPlanner",
        FakePlanner,
    )

    monkeypatch.setattr(
        service_module,
        "SemanticQueryEngine",
        FakeEngine,
    )


    service = build_service()


    result = (
        service
        .planned_inventory_query(
            "Show online virtual machines"
        )
    )


    assert (
        result is not None
    )

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert (
        result["llm_used"]
        is True
    )

    assert (
        result[
            "context_mode"
        ]
        == "semantic_planner"
    )

    assert (
        result[
            "semantic_planner_calls"
        ]
        == 1
    )

    assert calls[
        "execution"
    ] == {
        "question":
            "Show online virtual machines",

        "asset_types": [
            "VM",
        ],

        "statuses": [
            "ONLINE",
        ],
    }

    assert (
        "synthetic-alpha"
        in result[
            "answer"
        ]
    )


def test_non_inventory_plan_falls_through_without_registry_query(
    monkeypatch,
):

    import atlas.services.ai.semantic.pydantic_planner as planner_module
    import atlas.services.ai.service as service_module


    class FakePlanner:

        @classmethod
        def for_ollama(
            cls,
            **kwargs,
        ):

            return cls()


        def plan(
            self,
            question,
        ):

            return InventoryQueryPlan(
                intent="NONE",
                asset_types=[],
                statuses=[],
                reason=(
                    "not an inventory "
                    "request"
                ),
                confidence=0.99,
            )


    class ExplodingEngine:

        def __init__(
            self,
            *args,
            **kwargs,
        ):

            raise AssertionError(
                "Asset Registry executor "
                "must not run for NONE"
            )


    monkeypatch.setattr(
        planner_module,
        "PydanticInventoryPlanner",
        FakePlanner,
    )

    monkeypatch.setattr(
        service_module,
        "SemanticQueryEngine",
        ExplodingEngine,
    )


    service = build_service()


    result = (
        service
        .planned_inventory_query(
            "Restart the main machine"
        )
    )


    assert result is None


def test_ask_operator_uses_inventory_planner_before_knowledge_agent(
    monkeypatch,
):

    import atlas.mcp.client as knowledge_client_module


    class FakeKnowledgeClient:

        pass


    monkeypatch.setattr(
        knowledge_client_module,
        "MCPKnowledgeClient",
        FakeKnowledgeClient,
    )


    service = build_service()


    service.deterministic_semantic_query = (
        lambda question:
            None
    )

    service.deterministic_tool_query = (
        lambda question:
            None
    )

    service.planned_inventory_query = (
        lambda question:
            {
                "status":
                    "SUCCESS",

                "answer":
                    (
                        "synthetic planned "
                        "inventory"
                    ),

                "steps":
                    1,

                "model":
                    "synthetic-reasoning",

                "provider":
                    "ollama",

                "llm_used":
                    True,

                "tools_used":
                    [],

                "semantic_planner_calls":
                    1,

                "semantic_plan": {
                    "intent":
                        "INVENTORY",

                    "asset_types":
                        [],

                    "statuses":
                        [],
                },

                "context_mode":
                    "semantic_planner",

                "observations":
                    [],
            }
    )


    response = (
        service.ask_operator(
            AIRequest(
                task="reasoning",
                user_prompt=(
                    "What equipment "
                    "do I have?"
                ),
            )
        )
    )


    assert (
        response.content
        == "synthetic planned inventory"
    )

    assert (
        response.metadata[
            "llm_used"
        ]
        is True
    )

    assert (
        response.metadata[
            "mcp_agent"
        ]
        is False
    )

    assert (
        response.metadata[
            "planner_calls"
        ]
        == 0
    )

    assert (
        response.metadata[
            "semantic_planner_calls"
        ]
        == 1
    )

    assert (
        response.metadata[
            "context_mode"
        ]
        == "semantic_planner"
    )
