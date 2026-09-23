from atlas.services.context.operational import (
    OperationalContextBuilder,
)


def test_operational_context_schema():

    builder = OperationalContextBuilder()

    infrastructure = {
        "system": {
            "hostname": "test-host",
            "os": "test-os",
        },
        "assets": {
            "inventory": [],
        },
        "health": {
            "findings": [],
        },
    }

    intelligence = {
        "infrastructure": {},
        "assets": [],
        "health": {},
        "events": [],
        "incidents": [],
        "learning": [],
        "history": [],
        "knowledge": None,
        "operational_state": {},
        "actions": [],
        "recommendations": [],
        "ai_runtime": {},
    }

    result = builder._compose(
        infrastructure,
        intelligence,
    )

    assert result["schema_version"] == "1.0"

    expected_sections = [
        "system",
        "infrastructure",
        "assets",
        "topology",
        "health",
        "events",
        "incidents",
        "lifecycle",
        "history",
        "knowledge",
        "learning",
        "changes",
        "recommendations",
        "ai_runtime",
        "actions",
        "sources",
    ]

    for section in expected_sections:
        assert section in result

    assert "infrastructure_context" in result["sources"]
    assert "intelligence_context" in result["sources"]
