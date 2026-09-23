from atlas.services.ai.service import AIService

from atlas.services.intelligence.operator_tools.semantic import (
    SemanticTools,
)

from atlas.services.intelligence.operator_tools.synthesis import (
    can_synthesize_tool,
    synthesize_verified_tool_results,
)


class FakeSemantic:

    def attention(self):

        return {
            "status":
                "SUCCESS",

            "attention": {
                "state":
                    "WARNING",

                "attention_required":
                    True,

                "count":
                    1,

                "complete":
                    True,

                "items": [
                    {
                        "kind":
                            "INCIDENT",

                        "id":
                            "INC-SYNTHETIC",

                        "asset_id":
                            "asset-alpha",

                        "severity":
                            "HIGH",

                        "status":
                            "OPEN",

                        "title":
                            "synthetic_degradation",

                        "message":
                            (
                                "Synthetic operational "
                                "degradation."
                            ),
                    }
                ],
            },
        }


def test_attention_tool_is_declared():

    definitions = {
        definition.name:
            definition

        for definition
        in SemanticTools(
            semantic=FakeSemantic()
        ).definitions()
    }

    definition = definitions[
        "atlas_get_attention"
    ]

    assert (
        "OPERATIONAL_ATTENTION"
        in definition.capabilities
    )

    assert (
        "necesita atención"
        in definition.routing_hints
    )

    result = definition.execute()

    assert (
        result.status
        == "SUCCESS"
    )

    assert (
        result.result[
            "attention"
        ][
            "state"
        ]
        == "WARNING"
    )


def test_attention_has_verified_synthesis():

    assert can_synthesize_tool(
        "atlas_get_attention"
    )

    content = (
        synthesize_verified_tool_results(
            (
                "¿Qué necesita atención "
                "en mi infraestructura?"
            ),
            [
                {
                    "name":
                        "atlas_get_attention",

                    "result": {
                        "success":
                            True,

                        "data":
                            FakeSemantic().attention(),
                    },
                }
            ],
        )
    )

    assert content is not None
    assert "WARNING" in content
    assert "INC-SYNTHETIC" in content

    assert (
        "Synthetic operational degradation."
        in content
    )


def test_attention_routes_deterministically():

    result = (
        AIService()
        .deterministic_tool_query(
            (
                "¿Qué necesita atención "
                "en mi infraestructura y por qué?"
            )
        )
    )

    assert result is not None

    assert (
        result["tools"]
        == [
            "atlas_get_attention"
        ]
    )

    assert result["content"]


def test_attention_operator_metadata_is_deterministic():

    from atlas.services.ai.models import (
        AIRequest,
    )

    response = (
        AIService()
        .ask_operator(
            AIRequest(
                task="incident_reasoning",
                user_prompt=(
                    "¿Qué necesita atención "
                    "en mi infraestructura y por qué?"
                ),
            )
        )
    )

    metadata = (
        response.metadata
        or {}
    )

    assert (
        response.model
        == "atlas-tools"
    )

    assert (
        metadata[
            "deterministic"
        ]
        is True
    )

    assert (
        metadata[
            "llm_used"
        ]
        is False
    )

    assert (
        metadata[
            "mcp_agent"
        ]
        is False
    )

    assert (
        metadata[
            "planner_calls"
        ]
        == 0
    )

    assert (
        metadata[
            "context_mode"
        ]
        == "deterministic"
    )

    assert (
        metadata[
            "tools_used"
        ]
        == [
            "atlas_get_attention"
        ]
    )
