import pytest
from pydantic import ValidationError

from atlas.services.ai.operator.planning import (
    OperationPlan,
)
from atlas.services.ai.operator.pydantic_planner import (
    PydanticOperationPlanner,
)


class FakeRunResult:

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
        self.prompts = []


    def run_sync(
        self,
        prompt,
    ):

        self.prompts.append(
            prompt
        )

        return FakeRunResult(
            self.output
        )


def test_operation_plan_requires_target_for_proposal():

    with pytest.raises(
        ValidationError
    ):

        OperationPlan(
            intent="PROPOSE",
            action="start",
            target=None,
            reason="Requested start",
            confidence=1.0,
        )


def test_none_plan_cannot_smuggle_action():

    with pytest.raises(
        ValidationError
    ):

        OperationPlan(
            intent="NONE",
            action="restart",
            target="flaresolverr",
            reason="No operation",
            confidence=1.0,
        )


def test_pydantic_operation_planner_validates_dict_output():

    agent = FakeAgent(
        {
            "intent":
                "PROPOSE",

                "resource_type":
                    "container",

            "action":
                "restart",

            "target":
                "flaresolverr",

            "reason":
                "User explicitly requested restart",

            "confidence":
                0.99,
        }
    )

    planner = (
        PydanticOperationPlanner(
            agent
        )
    )


    plan = planner.plan(
        "Reiniciá flaresolverr",
        observations=[
            {
                "status":
                    "VERIFIED",
            }
        ],
    )


    assert (
        plan.intent
        == "PROPOSE"
    )

    assert (
        plan.action
        == "restart"
    )

    assert (
        plan.target
        == "flaresolverr"
    )

    assert (
        "VERIFIED"
        in agent.prompts[0]
    )


def test_pydantic_operation_planner_accepts_none():

    agent = FakeAgent(
        {
            "intent":
                "NONE",

            "action":
                None,

            "target":
                None,

            "reason":
                "Informational request",

            "confidence":
                1.0,
        }
    )

    planner = (
        PydanticOperationPlanner(
            agent
        )
    )


    plan = planner.plan(
        "¿Está funcionando flaresolverr?"
    )


    assert (
        plan.intent
        == "NONE"
    )

    assert (
        plan.action
        is None
    )

    assert (
        plan.target
        is None
    )


def test_pydantic_operation_planner_accepts_service_plan():

    agent = FakeAgent(
        {
            "intent":
                "PROPOSE",

            "resource_type":
                "service",

            "action":
                "restart",

            "target":
                "atlas-collector.service",

            "reason":
                "User explicitly requested service restart",

            "confidence":
                0.99,
        }
    )

    planner = (
        PydanticOperationPlanner(
            agent
        )
    )

    plan = planner.plan(
        "Reiniciá atlas-collector.service",
        observations=[],
    )

    assert plan.intent == "PROPOSE"
    assert plan.resource_type == "service"
    assert plan.action == "restart"
    assert plan.target == "atlas-collector.service"



def test_pydantic_operation_planner_accepts_vm_plan():

    agent = FakeAgent(
        {
            "intent": "PROPOSE",
            "resource_type": "vm",
            "action": "restart",
            "target": "200",
            "reason": "User explicitly requested VM restart",
            "confidence": 0.99,
        }
    )

    planner = PydanticOperationPlanner(
        agent
    )

    plan = planner.plan(
        "Reiniciá la VM 200",
        observations=[],
    )

    assert plan.intent == "PROPOSE"
    assert plan.resource_type == "vm"
    assert plan.action == "restart"
    assert plan.target == "200"


def test_pydantic_operation_planner_accepts_lxc_plan():

    agent = FakeAgent(
        {
            "intent": "PROPOSE",
            "resource_type": "lxc",
            "action": "stop",
            "target": "103",
            "reason": "User explicitly requested LXC stop",
            "confidence": 0.99,
        }
    )

    planner = PydanticOperationPlanner(
        agent
    )

    plan = planner.plan(
        "Detené el LXC 103",
        observations=[],
    )

    assert plan.intent == "PROPOSE"
    assert plan.resource_type == "lxc"
    assert plan.action == "stop"
    assert plan.target == "103"
