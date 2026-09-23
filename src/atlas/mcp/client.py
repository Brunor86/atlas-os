from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from mcp import Client

from atlas.mcp.server import (
    build_server,
)


@dataclass(slots=True)
class MCPToolExecutionResult:

    success: bool

    data: Any = None

    error: str | None = None

    evidence: list[str] = field(
        default_factory=list
    )


class MCPKnowledgeClient:
    """
    Synchronous read-only adapter over the ATLAS MCP server.

    OperatorAgent remains transport-agnostic: it only needs
    list_tools() and execute_tool().
    """

    def __init__(self):

        self._tool_cache = None


    @staticmethod
    def _run(
        coroutine,
    ):

        return asyncio.run(
            coroutine
        )


    async def _list_tools_async(self):

        async with Client(
            build_server()
        ) as client:

            return await client.list_tools()


    def list_tools(self):

        if self._tool_cache is not None:
            return list(
                self._tool_cache
            )

        result = self._run(
            self._list_tools_async()
        )

        tools = []

        for tool in result.tools:

            annotations = getattr(
                tool,
                "annotations",
                None,
            )

            read_only = bool(
                annotations
                and getattr(
                    annotations,
                    "read_only_hint",
                    False,
                )
            )

            #
            # atlas-knowledge must never expose a mutable
            # capability to the knowledge agent.
            #
            if not read_only:
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
                        True,

                    "requires_approval":
                        False,

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

        async with Client(
            build_server()
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

        allowed = {
            tool["name"]
            for tool in self.list_tools()
        }

        if name not in allowed:

            return MCPToolExecutionResult(
                success=False,
                error=(
                    "Unauthorized MCP knowledge tool: "
                    f"{name}"
                ),
                evidence=[
                    "atlas-knowledge MCP allowlist",
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
                error=str(exc),
                evidence=[
                    "atlas-knowledge MCP",
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
                else "SUCCESS",
            )
        ).upper()

        data = structured.get(
            "data",
            structured,
        )

        success = (
            not result.is_error
            and status == "SUCCESS"
        )

        error = None

        if not success:

            if isinstance(
                data,
                dict,
            ):
                error = data.get(
                    "error"
                )

            if not error:
                error = (
                    f"MCP tool {name} failed"
                )

        return MCPToolExecutionResult(
            success=success,
            data=data,
            error=error,
            evidence=[
                "atlas-knowledge MCP",
                f"tool:{name}",
            ],
        )
