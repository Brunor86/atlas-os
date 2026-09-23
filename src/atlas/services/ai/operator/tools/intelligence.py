from atlas.services.ai.operator.tools.base import (
    OperatorTool,
    OperatorToolResult,
)

from atlas.services.intelligence.operator_tools import (
    ToolRegistry,
)


class IntelligenceToolAdapter(OperatorTool):
    """
    Adapter between the AI operator tool interface and the
    existing ATLAS Intelligence ToolRegistry.

    The existing intelligence tools remain the source of truth.
    """

    @staticmethod
    def _registry_definition(
        registry,
        name: str,
    ):
        """
        Return the native ToolDefinition when the registry exposes
        the modern get() API.

        Legacy/test registries only need list/describe/execute and
        remain fully supported.
        """

        getter = getattr(
            registry,
            "get",
            None,
        )

        if not callable(
            getter
        ):
            return None

        try:
            return getter(
                name
            )
        except Exception:
            return None


    def __init__(
        self,
        registry: ToolRegistry,
        name: str,
        description: str,
    ):
        self.registry = registry
        self.name = name
        self.description = description

        definition = (
            self._registry_definition(
                self.registry,
                name,
            )
        )

        self.parameters = (
            definition.parameters
            if definition is not None
            else {
                "type": "object",
                "properties": {},
                "required": [],
            }
        )

        self.routing_hints = (
            definition.routing_hints
            if definition is not None
            else ()
        )

    def compact_result(
        self,
        result: dict,
    ) -> dict:

        definition = (
            self._registry_definition(
                self.registry,
                self.name,
            )
        )

        if definition is None:
            return result

        return definition.compact_result(
            result
        )


    def execute(
        self,
        **kwargs,
    ) -> OperatorToolResult:

        result = self.registry.execute(
            self.name,
            **kwargs,
        )

        return OperatorToolResult(
            tool=self.name,
            success=result.status == "SUCCESS",
            data=result.result,
            error=result.error,
            evidence=result.evidence,
        )


class IntelligenceToolBridge:

    def __init__(
        self,
        registry: ToolRegistry,
    ):
        self.registry = registry

    def tools(self):

        return [
            IntelligenceToolAdapter(
                registry=self.registry,
                name=tool["name"],
                description=tool["description"],
            )
            for tool in self.registry.describe()
        ]
