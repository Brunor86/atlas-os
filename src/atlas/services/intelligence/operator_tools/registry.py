
from atlas.services.intelligence.operator_tools.contracts import (
    get_tool_parameters,
    get_tool_result_compactor,
)
from atlas.services.intelligence.operator_tools.routing import (
    get_tool_routing_hints,
)
from atlas.services.intelligence.operator_tools.base import (
    ToolDefinition,
    ToolResult,
)


class ToolRegistry:

    def __init__(self):

        self._tools: dict[
            str,
            ToolDefinition,
        ] = {}


    def register(
        self,
        tool: ToolDefinition,
    ):

        # ---------------------------------------------------------
        # Complete the runtime ToolDefinition contract from
        # declarative tool-layer metadata.
        # ---------------------------------------------------------

        tool.parameters = (
            get_tool_parameters(
                tool.name
            )
        )

        if not tool.routing_hints:

            tool.routing_hints = tuple(
                get_tool_routing_hints(
                    tool.name
                )
            )

        if tool.result_compactor is None:

            tool.result_compactor = (
                get_tool_result_compactor(
                    tool.name
                )
            )

        if tool.name in self._tools:

            raise ValueError(
                f"Tool already registered: {tool.name}"
            )

        self._tools[
            tool.name
        ] = tool


    def register_many(
        self,
        tools,
    ):

        for tool in tools:
            self.register(tool)


    def get(
        self,
        name: str,
    ):

        return self._tools.get(
            name
        )


    def list(
        self,
    ):

        return list(
            self._tools.values()
        )


    def describe(
        self,
    ):

        return [

            {
                "name":
                    tool.name,

                "description":
                    tool.description,

                "read_only":
                    tool.read_only,

                "requires_approval":
                    tool.requires_approval,

                "capabilities":
                    list(tool.capabilities),

            }

            for tool in self._tools.values()

        ]


    def execute(
        self,
        name: str,
        **kwargs,
    ) -> ToolResult:

        tool = self.get(
            name
        )

        if not tool:

            return ToolResult(

                tool=name,

                status="ERROR",

                error=(
                    f"Unknown tool: {name}"
                ),

            )

        try:

            return tool.execute(
                **kwargs
            )

        except Exception as exc:

            return ToolResult(

                tool=name,

                status="ERROR",

                error=str(exc),

            )
