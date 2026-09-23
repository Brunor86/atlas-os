import pytest
from pydantic import ValidationError

from atlas.services.ai.operator.tools.base import (
    OperatorToolResult,
)


def test_tool_result_is_pydantic_contract():

    result = OperatorToolResult(
        tool="get_asset",
        success=True,
        data={
            "asset_id": "docker-host",
        },
        evidence=[
            "asset discovered",
        ],
    )

    assert result.tool == "get_asset"
    assert result.success is True
    assert result.data["asset_id"] == "docker-host"
    assert result.evidence == ["asset discovered"]


def test_tool_result_defaults_are_safe():

    result = OperatorToolResult(
        tool="get_asset",
        success=False,
    )

    assert result.data is None
    assert result.error is None
    assert result.evidence == []


def test_tool_result_rejects_empty_tool_name():

    with pytest.raises(ValidationError):
        OperatorToolResult(
            tool="",
            success=True,
        )


def test_tool_result_rejects_unknown_fields():

    with pytest.raises(ValidationError):
        OperatorToolResult(
            tool="get_asset",
            success=True,
            unexpected="value",
        )


def test_tool_result_serializes_cleanly():

    result = OperatorToolResult(
        tool="diagnose",
        success=False,
        error="tool execution failed",
        evidence=[
            {"source": "docker"},
            {"source": "network"},
        ],
    )

    dumped = result.model_dump()

    assert dumped == {
        "tool": "diagnose",
        "success": False,
        "data": None,
        "error": "tool execution failed",
        "evidence": [
            {"source": "docker"},
            {"source": "network"},
        ],
    }


def test_tool_result_accepts_structured_data():

    result = OperatorToolResult(
        tool="topology",
        success=True,
        data={
            "root": "docker-host",
            "children": [
                "jellyseerr",
                "sonarr",
            ],
        },
    )

    assert result.data["root"] == "docker-host"
    assert len(result.data["children"]) == 2


def test_tool_result_assignment_is_validated():

    result = OperatorToolResult(
        tool="diagnose",
        success=True,
    )

    with pytest.raises(ValidationError):
        result.tool = ""


def test_tool_result_evidence_is_not_shared_between_instances():

    first = OperatorToolResult(
        tool="one",
        success=True,
    )

    second = OperatorToolResult(
        tool="two",
        success=True,
    )

    first.evidence.append("evidence")

    assert first.evidence == ["evidence"]
    assert second.evidence == []
