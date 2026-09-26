import json

from types import SimpleNamespace

from atlas.services.ai.models import (
    AIRequest,
)

from atlas.services.ai.operator.planning import (
    OperationPlan,
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


class FakeProvider:

    def available(
        self,
    ):
        return True


    def generate(
        self,
        prompt,
        model,
        **kwargs,
    ):
        return json.dumps(
            {
                "action":
                    "final",

                "answer":
                    "synthetic planning complete",
            }
        )


def build_synthetic_operator(
    monkeypatch,
    *,
    operation_action,
):

    import atlas.mcp.client as knowledge_client_module

    import atlas.mcp.operator_client as operator_client_module

    import atlas.services.ai.agent.agent as agent_module

    import atlas.services.ai.operator.pydantic_planner as planner_module

    import atlas.services.ai.operator.target_resolver as resolver_module


    proposal_calls = []
    activity = []


    class FakeKnowledgeClient:

        pass


    class FakeAgent:

        def __init__(
            self,
            ai_service,
            *,
            planner,
            **kwargs,
        ):
            self.planner = planner


        def run(
            self,
            user_request,
        ):

            raise AssertionError(
                "Knowledge Agent must not run "
                "for explicit operation candidates"
            )


    class FakeOperationPlanner:

        @classmethod
        def for_ollama(
            cls,
            **kwargs,
        ):
            return cls()


        def plan(
            self,
            question,
            *,
            observations=None,
        ):
            return OperationPlan(
                intent="PROPOSE",
                resource_type=None,
                action=operation_action,
                target="olivasat",
                reason=(
                    "explicit synthetic "
                    "named-target request"
                ),
                confidence=0.99,
            )


    class FakeTargetResolver:

        def resolve(
            self,
            query,
            *,
            requested_resource_type=None,
        ):

            assert query == "olivasat"

            assert (
                requested_resource_type
                is None
            )

            return SimpleNamespace(
                status="RESOLVED",
                query="olivasat",
                resource_type="lxc",
                target="103",
                asset_id=(
                    "lxc-proxmox-"
                    "linux_container-103"
                ),
                asset_name="olivasat",
                reason=(
                    "resolved from active "
                    "ATLAS asset registry"
                ),
                candidates=(),
            )


    class FakeOperatorClient:

        def __init__(
            self,
        ):
            proposal_calls.append(
                {
                    "event":
                        "client_constructed",
                }
            )


        def execute_tool(
            self,
            name,
            **kwargs,
        ):

            proposal_calls.append(
                {
                    "event":
                        "proposal",

                    "tool":
                        name,

                    **kwargs,
                }
            )

            return SimpleNamespace(
                success=True,

                data={
                    "status":
                        "PENDING_APPROVAL",

                    "resource_type":
                        "lxc",

                    "action_request": {
                        "id":
                            "ACTION-SYNTHETIC-103",

                        "action":
                            (
                                operation_action
                                + " lxc"
                            ),

                        "target":
                            "103",

                        "risk":
                            (
                                "MEDIUM"
                                if operation_action
                                == "restart"
                                else "HIGH"
                            ),

                        "status":
                            "PENDING_APPROVAL",
                    },

                    "target_state":
                        "RUNNING",

                    "requires_approval":
                        True,

                    "execution_allowed":
                        False,
                },

                error=None,

                evidence=[
                    "synthetic operator MCP",
                ],
            )


    monkeypatch.setattr(
        knowledge_client_module,
        "MCPKnowledgeClient",
        FakeKnowledgeClient,
    )

    monkeypatch.setattr(
        agent_module,
        "OperatorAgent",
        FakeAgent,
    )

    monkeypatch.setattr(
        planner_module,
        "PydanticOperationPlanner",
        FakeOperationPlanner,
    )

    monkeypatch.setattr(
        resolver_module,
        "OperationTargetResolver",
        FakeTargetResolver,
    )

    monkeypatch.setattr(
        operator_client_module,
        "MCPOperatorClient",
        FakeOperatorClient,
    )


    service = AIService.__new__(
        AIService
    )

    runtime = FakeRuntime()

    service.runtime = runtime

    service.runtime_target = (
        SimpleNamespace(
            provider="ollama",
            url=(
                "ollama://"
                "127.0.0.1:11434"
            ),
        )
    )

    service.providers = {
        "ollama":
            FakeProvider(),
    }


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
            runtime.events.append(
                (
                    "unload",
                    selected.name,
                )
            )
    )


    def callback(
        event,
        data,
    ):
        activity.append(
            (
                event,
                data,
            )
        )


    return (
        service,
        runtime,
        proposal_calls,
        activity,
        callback,
    )


def test_restart_olivasat_reaches_pending_approval_only(
    monkeypatch,
):

    (
        service,
        runtime,
        proposal_calls,
        activity,
        callback,
    ) = build_synthetic_operator(
        monkeypatch,
        operation_action="restart",
    )


    response = service.ask_operator(
        AIRequest(
            task="incident_reasoning",
            user_prompt="restart olivasat",
        ),
        event_callback=callback,
    )


    assert (
        response.metadata[
            "context_mode"
        ]
        == "operator"
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


    assert proposal_calls == [
        {
            "event":
                "client_constructed",
        },
        {
            "event":
                "proposal",

            "tool":
                (
                    "atlas_propose_"
                    "proxmox_guest_action"
                ),

            "action":
                "restart",

            "target":
                "103",

            "resource_type":
                "lxc",
        },
    ]


    proposals = [
        data
        for event, data
        in activity
        if event
        == "operation_proposed"
    ]


    assert len(
        proposals
    ) == 1


    proposal = proposals[0]


    assert (
        proposal[
            "status"
        ]
        == "PENDING_APPROVAL"
    )

    assert (
        proposal[
            "execution_allowed"
        ]
        is False
    )

    assert (
        proposal[
            "plan"
        ][
            "resource_type"
        ]
        == "lxc"
    )

    assert (
        proposal[
            "plan"
        ][
            "target"
        ]
        == "103"
    )

    assert (
        proposal[
            "requested_plan"
        ][
            "target"
        ]
        == "olivasat"
    )

    assert (
        proposal[
            "target_resolution"
        ][
            "asset_name"
        ]
        == "olivasat"
    )

    assert (
        proposal[
            "target_resolution"
        ][
            "target"
        ]
        == "103"
    )


    assert (
        "Human approval is required"
        in response.content
    )


    assert (
        (
            "unload",
            "synthetic-reasoning",
        )
        in runtime.events
    )

    assert (
        (
            "unload_all",
        )
        in runtime.events
    )


def test_stop_olivasat_reaches_high_risk_pending_approval_only(
    monkeypatch,
):

    (
        service,
        runtime,
        proposal_calls,
        activity,
        callback,
    ) = build_synthetic_operator(
        monkeypatch,
        operation_action="stop",
    )


    response = service.ask_operator(
        AIRequest(
            task="incident_reasoning",
            user_prompt="stop olivasat",
        ),
        event_callback=callback,
    )


    assert proposal_calls == [
        {
            "event":
                "client_constructed",
        },
        {
            "event":
                "proposal",

            "tool":
                (
                    "atlas_propose_"
                    "proxmox_guest_action"
                ),

            "action":
                "stop",

            "target":
                "103",

            "resource_type":
                "lxc",
        },
    ]


    proposals = [
        data
        for event, data
        in activity
        if event
        == "operation_proposed"
    ]


    assert len(
        proposals
    ) == 1


    proposal = proposals[0]


    assert (
        proposal[
            "status"
        ]
        == "PENDING_APPROVAL"
    )

    assert (
        proposal[
            "execution_allowed"
        ]
        is False
    )

    assert (
        proposal[
            "action_request"
        ][
            "action"
        ]
        == "stop lxc"
    )

    assert (
        proposal[
            "action_request"
        ][
            "risk"
        ]
        == "HIGH"
    )

    assert (
        proposal[
            "plan"
        ][
            "resource_type"
        ]
        == "lxc"
    )

    assert (
        proposal[
            "plan"
        ][
            "target"
        ]
        == "103"
    )

    assert (
        proposal[
            "requested_plan"
        ][
            "target"
        ]
        == "olivasat"
    )

    assert (
        proposal[
            "target_resolution"
        ][
            "asset_name"
        ]
        == "olivasat"
    )

    assert (
        "Human approval is required"
        in response.content
    )


    blocked = [
        data
        for event, data
        in activity
        if event
        == "operation_blocked"
    ]

    assert blocked == []


    assert (
        (
            "unload",
            "synthetic-reasoning",
        )
        in runtime.events
    )

    assert (
        (
            "unload_all",
        )
        in runtime.events
    )
