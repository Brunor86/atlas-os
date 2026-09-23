from atlas.services.ai.operator.operator import AIModelOperator
from atlas.services.intelligence.operator_tools.registry import ToolRegistry
from atlas.services.intelligence.operator_tools.assets import AssetTools


def test_ai_operator_exposes_real_asset_intelligence_tools():

    registry = ToolRegistry()

    asset_tools = AssetTools()

    for tool in asset_tools.definitions():
        registry.register(tool)

    operator = AIModelOperator(
        tool_registry=registry,
    )

    tools = operator.list_tools()

    names = {
        tool.name
        for tool in tools
    }

    assert "find_asset" in names
    assert "get_asset_context" in names
    assert "list_assets" in names
    assert "inspect_asset" in names


def test_ai_operator_preserves_real_tool_metadata():

    registry = ToolRegistry()

    asset_tools = AssetTools()

    for tool in asset_tools.definitions():
        registry.register(tool)

    operator = AIModelOperator(
        tool_registry=registry,
    )

    tool = operator.get_tool(
        "list_assets"
    )

    assert tool is not None

    assert tool.name == "list_assets"

    assert tool.description

    result = operator.execute_tool(
        "list_assets"
    )

    assert result.tool == "list_assets"

    assert result.success is True

    assert isinstance(
        result.data,
        list,
    )

    assert isinstance(
        result.evidence,
        list,
    )


def test_ai_operator_real_asset_tool_execution_preserves_contract():

    registry = ToolRegistry()

    asset_tools = AssetTools()

    for tool in asset_tools.definitions():
        registry.register(tool)

    operator = AIModelOperator(
        tool_registry=registry,
    )

    result = operator.execute_tool(
        "find_asset",
        query="jellyseerr",
    )

    assert result.tool == "find_asset"

    assert result.success is True

    assert isinstance(
        result.data,
        list,
    )

    assert isinstance(
        result.evidence,
        list,
    )


def test_ai_operator_unknown_tool_is_safe():

    registry = ToolRegistry()

    operator = AIModelOperator(
        tool_registry=registry,
    )

    result = operator.execute_tool(
        "does_not_exist",
    )

    assert result.tool == "does_not_exist"

    assert result.success is False

    assert result.error is not None
