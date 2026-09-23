from __future__ import annotations

import asyncio

from atlas.mcp.client import (
    MCPToolExecutionResult,
)
from atlas.mcp.operator_server import (
    build_operator_server,
)


class MCPOperatorClient:
    """
    Narrow synchronous client for atlas-operator MCP.

    This client intentionally exposes ONLY proposal capabilities.

    It cannot:

        approve
        execute
        reject
        shell
        exec

    Human approval and infrastructure execution remain outside
    this client.
    """

    ALLOWED_TOOLS = {
        "atlas_propose_container_action",
        "atlas_propose_service_action",
        "atlas_propose_proxmox_guest_action",
    }


    def __init__(
        self,
        server_builder=None,
    ):

        self._server_builder = (
            server_builder
            or build_operator_server
        )

        self._tool_cache = None


    @staticmethod
    def _run(
        coroutine,
    ):

        return asyncio.run(
            coroutine
        )


    async def _list_tools_async(
        self,
    ):

        from mcp import Client

        async with Client(
            self._server_builder()
        ) as client:

            return (
                await client.list_tools()
            )


    def list_tools(
        self,
    ):

        if (
            self._tool_cache
            is not None
        ):

            return list(
                self._tool_cache
            )


        result = self._run(
            self._list_tools_async()
        )


        tools = []


        for tool in result.tools:

            if (
                tool.name
                not in self.ALLOWED_TOOLS
            ):
                continue


            annotations = getattr(
                tool,
                "annotations",
                None,
            )


            #
            # atlas-operator proposal tools must be mutable from the
            # MCP protocol perspective because they persist a request.
            #
            # However, they are NOT execution capabilities.
            #
            if (
                annotations is None
                or getattr(
                    annotations,
                    "read_only_hint",
                    True,
                )
            ):
                continue


            parameters = getattr(
                tool,
                "input_schema",
                None,
            )

            if not isinstance(
                parameters,
                dict,
            ):

                parameters = {
                    "type": "object",
                    "properties": {},
                }


            tools.append(
                {
                    "name":
                        tool.name,

                    "description":
                        tool.description
                        or "",

                    "read_only":
                        False,

                    "requires_approval":
                        True,

                    "parameters":
                        parameters,
                }
            )


        self._tool_cache = tuple(
            tools
        )

        return list(
            self._tool_cache
        )


    async def _execute_async(
        self,
        name,
        arguments,
    ):

        from mcp import Client

        async with Client(
            self._server_builder()
        ) as client:

            return await client.call_tool(
                name,
                arguments,
            )


    def execute_tool(
        self,
        name,
        **kwargs,
    ) -> MCPToolExecutionResult:

        if (
            name
            not in self.ALLOWED_TOOLS
        ):

            return MCPToolExecutionResult(
                success=False,
                error=(
                    "Unauthorized MCP operator tool: "
                    f"{name}"
                ),
                evidence=[
                    "atlas-operator MCP allowlist",
                ],
            )


        available = {
            tool["name"]
            for tool in self.list_tools()
        }


        if (
            name
            not in available
        ):

            return MCPToolExecutionResult(
                success=False,
                error=(
                    "Unavailable MCP operator tool: "
                    f"{name}"
                ),
                evidence=[
                    "atlas-operator MCP capability boundary",
                ],
            )


        try:

            result = self._run(
                self._execute_async(
                    name,
                    kwargs,
                )
            )

        except Exception as exc:

            return MCPToolExecutionResult(
                success=False,
                error=str(
                    exc
                ),
                evidence=[
                    "atlas-operator MCP",
                ],
            )


        structured = (
            result.structured_content
            if isinstance(
                result.structured_content,
                dict,
            )
            else {}
        )


        status = str(
            structured.get(
                "status",
                "ERROR"
                if result.is_error
                else "UNKNOWN",
            )
        ).upper()


        data = structured.get(
            "data",
            structured,
        )


        success = (
            not result.is_error
            and status
            == "PENDING_APPROVAL"
        )


        error = None


        if not success:

            if isinstance(
                data,
                dict,
            ):

                error = (
                    data.get(
                        "reason"
                    )
                    or data.get(
                        "error"
                    )
                )


            if not error:

                error = (
                    "MCP operator proposal failed "
                    f"with status {status}"
                )


        return MCPToolExecutionResult(
            success=success,
            data=data,
            error=error,
            evidence=[
                "atlas-operator MCP",
                f"tool:{name}",
                f"status:{status}",
            ],
        )
