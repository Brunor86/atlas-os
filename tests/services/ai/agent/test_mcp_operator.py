from types import SimpleNamespace

from atlas.mcp.client import (
    MCPKnowledgeClient,
)
from atlas.services.ai.agent.agent import (
    OperatorAgent,
)


def test_mcp_client_exposes_only_read_only_tools():

    client = MCPKnowledgeClient()

    tools = client.list_tools()

    assert tools

    assert all(
        tool["read_only"]
        for tool in tools
    )

    assert all(
        not tool["requires_approval"]
        for tool in tools
    )

    assert all(
        isinstance(
            tool["parameters"],
            dict,
        )
        for tool in tools
    )


def test_mcp_client_can_search_synthetic_asset(mcp_synthetic_runtime):

    client = MCPKnowledgeClient()

    result = client.execute_tool(
        "atlas_search_assets",
        query="suite-alpha",
        limit=10,
    )

    assert result.success

    names = {
        item["name"]
        for item in result.data[
            "matches"
        ]
    }

    assert "app-alpha" in names


class FakeKnowledgeBackend:

    def __init__(self):

        self.calls = []


    def list_tools(self):

        return [
            {
                "name":
                    "atlas_search_assets",

                "description":
                    "Search assets",

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

                    "required": [
                        "query",
                    ],
                },
            }
        ]


    def execute_tool(
        self,
        name,
        **kwargs,
    ):

        self.calls.append(
            (
                name,
                kwargs,
            )
        )

        return SimpleNamespace(
            success=True,
            data={
                "matches": [
                    {
                        "id":
                            "application-example",

                        "name":
                            "example",
                    }
                ]
            },
            error=None,
            evidence=[
                "fake MCP",
            ],
        )


class FakeAI:

    def __init__(self):

        self.requests = []


    def deterministic_semantic_query(
        self,
        prompt,
    ):

        return None


    def deterministic_tool_query(
        self,
        prompt,
    ):

        return None


    def ask(
        self,
        request,
    ):

        self.requests.append(
            request
        )

        if len(
            self.requests
        ) == 1:

            return SimpleNamespace(
                model="planner",
                provider="ollama",
                content=(
                    '{"action":"tool",'
                    '"tool":"atlas_search_assets",'
                    '"arguments":{"query":"example"},'
                    '"reason":"locate entity"}'
                ),
            )

        return SimpleNamespace(
            model="planner",
            provider="ollama",
            content=(
                '{"action":"final",'
                '"answer":"example found"}'
            ),
        )


def test_operator_uses_mcp_backend_and_small_agent_request():

    ai = FakeAI()

    backend = FakeKnowledgeBackend()

    agent = OperatorAgent(
        ai,
        tool_backend=backend,
    )

    result = agent.run(
        "Find example"
    )

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert (
        result["answer"]
        == "example found"
    )

    assert backend.calls == [
        (
            "atlas_search_assets",
            {
                "query":
                    "example",
            },
        )
    ]

    assert (
        ai.requests[0]
        .context_required
        is False
    )

    assert (
        '"parameters"'
        in ai.requests[0]
        .user_prompt
    )


def test_operator_uses_injected_planner_instead_of_ai_ask():

    backend = FakeKnowledgeBackend()

    class AIWithoutAsk:

        def deterministic_semantic_query(
            self,
            prompt,
        ):
            return None

        def deterministic_tool_query(
            self,
            prompt,
        ):
            return None

        def ask(
            self,
            request,
        ):
            raise AssertionError(
                "AIService.ask must not be used "
                "when planner is injected"
            )

    calls = []

    def planner(request):

        calls.append(
            request
        )

        if len(calls) == 1:

            return SimpleNamespace(
                model="planner",
                provider="ollama",
                content=(
                    '{"action":"tool",'
                    '"tool":"atlas_search_assets",'
                    '"arguments":{"query":"example"},'
                    '"reason":"locate entity"}'
                ),
            )

        return SimpleNamespace(
            model="planner",
            provider="ollama",
            content=(
                '{"action":"final",'
                '"answer":"done"}'
            ),
        )

    agent = OperatorAgent(
        AIWithoutAsk(),
        tool_backend=backend,
        planner=planner,
    )

    result = agent.run(
        "Find example"
    )

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert (
        result["answer"]
        == "done"
    )

    assert len(calls) == 2

    assert all(
        request.context_required
        is False
        for request in calls
    )
