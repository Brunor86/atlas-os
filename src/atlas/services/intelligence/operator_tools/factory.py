from atlas.services.intelligence.operator_tools.base import (
    ToolDefinition,
)

from atlas.services.intelligence.operator_tools.registry import (
    ToolRegistry,
)

from atlas.services.intelligence.operator_tools.assets import (
    AssetTools,
)

from atlas.services.intelligence.operator_tools.telemetry import (
    TelemetryTools,
)

from atlas.services.intelligence.operator_tools.semantic import (
    SemanticTools,
)


def build_operator_tool_registry(
    *,
    asset_repository=None,
    telemetry=None,
) -> ToolRegistry:

    registry = ToolRegistry()

    asset_tools = AssetTools(
        repository=asset_repository,
    )

    telemetry_tools = TelemetryTools(
        telemetry=telemetry,
    )

    semantic_tools = SemanticTools()

    registry.register_many(
        asset_tools.definitions()
    )

    registry.register_many(
        telemetry_tools.definitions()
    )

    registry.register_many(
        semantic_tools.definitions()
    )

    return registry
