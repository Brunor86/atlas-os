import json

from types import SimpleNamespace

from atlas.services.ai.agent.agent import (
    OperatorAgent,
)


class FakeAI:
    pass


class FakeKnowledgeBackend:

    def list_tools(self):

        return [
            {
                "name":
                    "atlas_search_assets",

                "description":
                    "Synthetic asset search",

                "read_only":
                    True,

                "requires_approval":
                    False,

                "parameters": {
                    "type":
                        "object",

                    "properties": {
                        "query": {
                            "type":
                                "string",
                        },
                    },
                },
            }
        ]


    def execute_tool(
        self,
        name,
        **kwargs,
    ):

        return SimpleNamespace(
            success=True,
            data={
                "status":
                    "SUCCESS",

                "matches": [],
            },
            error=None,
            evidence=[
                "synthetic MCP result",
            ],
        )


def test_operator_emits_real_tool_activity():

    events = []

    decisions = iter(
        [
            {
                "action":
                    "tool",

                "tool":
                    "atlas_search_assets",

                "arguments": {
                    "query":
                        "node-alpha",
                },

                "reason":
                    "resolve entity",
            },

            {
                "action":
                    "final",

                "answer":
                    "Synthetic answer.",
            },
        ]
    )


    def planner(
        request,
    ):

        return SimpleNamespace(
            model="synthetic-model",
            provider="synthetic",
            content=json.dumps(
                next(decisions)
            ),
            latency_ms=1.0,
        )


    def callback(
        event,
        data,
    ):

        events.append(
            (
                event,
                data,
            )
        )


    agent = OperatorAgent(
        FakeAI(),
        max_steps=3,
        tool_backend=(
            FakeKnowledgeBackend()
        ),
        planner=planner,
        semantic_preflight=False,
        tool_preflight=False,
        event_callback=callback,
    )


    result = agent.run(
        "Inspect node-alpha"
    )


    assert (
        result["status"]
        == "SUCCESS"
    )

    names = [
        event
        for event, _
        in events
    ]

    assert (
        "planner_started"
        in names
    )

    assert (
        "planner_completed"
        in names
    )

    assert (
        "tool_started"
        in names
    )

    assert (
        "tool_completed"
        in names
    )

    assert (
        "answer_ready"
        in names
    )


    started_index = (
        names.index(
            "tool_started"
        )
    )

    completed_index = (
        names.index(
            "tool_completed"
        )
    )

    assert (
        started_index
        < completed_index
    )
