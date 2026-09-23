from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(slots=True)
class ToolResult:

    tool: str

    status: str

    result: Any = None

    error: str | None = None

    evidence: list[str] = field(
        default_factory=list
    )


@dataclass(slots=True)
class ToolDefinition:

    name: str

    description: str

    handler: Callable[..., ToolResult]

    read_only: bool = True

    requires_approval: bool = False

    capabilities: tuple[str, ...] = ()

    # JSON-schema compatible arguments exposed to AI/tool callers.
    parameters: dict[str, Any] = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {},
            "required": [],
        }
    )

    # Declarative natural-language routing metadata.
    routing_hints: tuple[str, ...] = ()

    # Optional tool-layer compactor for LLM-facing results.
    result_compactor: Callable[
        [dict],
        dict,
    ] | None = None

    def execute(
        self,
        **kwargs,
    ) -> ToolResult:

        return self.handler(
            **kwargs
        )

    def compact_result(
        self,
        result: dict,
    ) -> dict:

        if self.result_compactor is None:
            return result

        return self.result_compactor(
            result
        )
