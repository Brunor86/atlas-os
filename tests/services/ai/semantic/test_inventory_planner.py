import pytest

from pydantic import (
    ValidationError,
)

from atlas.services.ai.semantic.planning import (
    InventoryQueryPlan,
)

from atlas.services.ai.semantic.pydantic_planner import (
    INVENTORY_PLANNER_INSTRUCTIONS,
    PydanticInventoryPlanner,
)


class FakeResult:

    def __init__(
        self,
        output,
    ):

        self.output = output


class FakeAgent:

    def __init__(
        self,
        output,
    ):

        self.output = output
        self.requests = []


    def run_sync(
        self,
        request,
    ):

        self.requests.append(
            request
        )

        return FakeResult(
            self.output
        )


def test_inventory_plan_accepts_broad_inventory():

    plan = InventoryQueryPlan(
        intent="INVENTORY",
        asset_types=[],
        statuses=[],
        reason="Broad inventory request",
        confidence=0.95,
    )

    assert (
        plan.intent
        == "INVENTORY"
    )

    assert (
        plan.asset_types
        == []
    )

    assert (
        plan.statuses
        == []
    )


def test_inventory_plan_accepts_multi_type_status():

    plan = InventoryQueryPlan(
        intent="INVENTORY",
        asset_types=[
            "SERVER",
            "VM",
        ],
        statuses=[
            "ONLINE",
        ],
        reason="Structured inventory request",
        confidence=0.98,
    )

    assert set(
        plan.asset_types
    ) == {
        "SERVER",
        "VM",
    }

    assert (
        plan.statuses
        == [
            "ONLINE",
        ]
    )


def test_none_cannot_smuggle_selectors():

    with pytest.raises(
        ValidationError,
        match="NONE",
    ):

        InventoryQueryPlan(
            intent="NONE",
            asset_types=[
                "VM",
            ],
            statuses=[],
            reason="Not inventory",
            confidence=1.0,
        )


def test_duplicate_selectors_are_rejected():

    with pytest.raises(
        ValidationError,
        match="duplicates",
    ):

        InventoryQueryPlan(
            intent="INVENTORY",
            asset_types=[
                "VM",
                "VM",
            ],
            statuses=[],
            reason="Duplicate selector",
            confidence=1.0,
        )


def test_planner_validates_mapping_output():

    agent = FakeAgent(
        {
            "intent":
                "INVENTORY",

            "asset_types": [
                "SERVER",
                "VM",
            ],

            "statuses": [
                "ONLINE",
            ],

            "reason":
                "User requested running compute assets",

            "confidence":
                0.96,
        }
    )

    planner = (
        PydanticInventoryPlanner(
            agent
        )
    )

    plan = planner.plan(
        "Show running servers and virtual machines"
    )

    assert isinstance(
        plan,
        InventoryQueryPlan,
    )

    assert set(
        plan.asset_types
    ) == {
        "SERVER",
        "VM",
    }

    assert (
        plan.statuses
        == [
            "ONLINE",
        ]
    )

    assert agent.requests == [
        "Show running servers and virtual machines"
    ]


def test_blank_question_is_rejected():

    planner = (
        PydanticInventoryPlanner(
            FakeAgent(
                {
                    "intent":
                        "NONE",

                    "asset_types":
                        [],

                    "statuses":
                        [],

                    "reason":
                        "No request",

                    "confidence":
                        1.0,
                }
            )
        )
    )

    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):

        planner.plan(
            "   "
        )


def test_planner_contains_no_tool_backend():

    planner = (
        PydanticInventoryPlanner(
            FakeAgent(
                {
                    "intent":
                        "NONE",

                    "asset_types":
                        [],

                    "statuses":
                        [],

                    "reason":
                        "Not inventory",

                    "confidence":
                        1.0,
                }
            )
        )
    )

    assert not hasattr(
        planner,
        "tool_backend",
    )

    assert not hasattr(
        planner,
        "execute_tool",
    )


def test_instructions_forbid_infrastructure_invention():

    normalized = " ".join(
        INVENTORY_PLANNER_INSTRUCTIONS.split()
    )

    assert (
        "no access to current Asset Registry contents"
        in normalized
    )

    assert (
        "must never invent asset names"
        in normalized
    )

    assert (
        "must not be forced into a specific asset type"
        in normalized
    )

    assert (
        "ATLAS performs all actual inventory queries deterministically"
        in normalized
    )



def test_inventory_intent_is_required():

    with pytest.raises(
        ValidationError,
    ):

        InventoryQueryPlan(
            asset_types=[],
            statuses=[],
            reason="Intent omitted",
            confidence=1.0,
        )


def test_inventory_schema_requires_intent():

    schema = (
        InventoryQueryPlan
        .model_json_schema()
    )

    assert (
        "intent"
        in schema[
            "required"
        ]
    )
