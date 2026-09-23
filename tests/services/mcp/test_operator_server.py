import asyncio

from mcp import Client

from atlas.mcp.operator_server import (
    build_operator_server,
)


class FakeProposalService:

    def __init__(self):

        self.calls = []


    def propose_container_action(
        self,
        action,
        target,
    ):

        self.calls.append(
            {
                "action": action,
                "target": target,
            }
        )

        return {
            "status":
                "PENDING_APPROVAL",

            "action_request": {
                "id":
                    "ACTION-TEST",

                "action":
                    f"{action} container",

                "target":
                    target,

                "risk":
                    "LOW",

                "status":
                    "PENDING_APPROVAL",
            },

            "target_state":
                "RUNNING",

            "safety": {
                "validated":
                    True,

                "risk":
                    "LOW",
            },

            "requires_approval":
                True,

            "execution_allowed":
                False,
        }

    def propose_service_action(
        self,
        action,
        target,
    ):

        self.calls.append(
            {
                "action":
                    action,

                "target":
                    target,
            }
        )

        return {
            "status":
                "PENDING_APPROVAL",

            "resource_type":
                "service",

            "action_request": {
                "id":
                    "ACTION-SERVICE-TEST",

                "action":
                    f"{action} service",

                "target":
                    target,

                "risk":
                    "LOW",

                "status":
                    "PENDING_APPROVAL",
            },

            "target_state":
                "RUNNING",

            "safety": {
                "validated":
                    True,

                "risk":
                    "LOW",
            },

            "requires_approval":
                True,

            "execution_allowed":
                False,
        }


    def propose_proxmox_guest_action(
        self,
        resource_type,
        action,
        target,
    ):

        self.calls.append(
            {
                "resource_type": resource_type,
                "action": action,
                "target": target,
            }
        )

        return {
            "status": "PENDING_APPROVAL",
            "resource_type": resource_type,

            "action_request": {
                "id": "ACTION-PROXMOX-TEST",
                "action": f"{action} {resource_type}",
                "target": target,
                "risk": "MEDIUM",
                "status": "PENDING_APPROVAL",
            },

            "target_state": "RUNNING",

            "safety": {
                "validated": True,
                "risk": "MEDIUM",
            },

            "requires_approval": True,
            "execution_allowed": False,
        }



def run(
    coroutine,
):
    return asyncio.run(
        coroutine
    )


async def list_tools(
    server,
):

    async with Client(
        server
    ) as client:

        return await client.list_tools()


async def call(
    server,
    name,
    arguments,
):

    async with Client(
        server
    ) as client:

        return await client.call_tool(
            name,
            arguments,
        )


def test_operator_mcp_exposes_only_proposal_tool():

    fake = FakeProposalService()

    server = build_operator_server(
        proposal_service=fake
    )

    result = run(
        list_tools(
            server
        )
    )

    tools = {
        tool.name:
            tool
        for tool in result.tools
    }

    assert set(
        tools
    ) == {
        "atlas_propose_container_action",
        "atlas_propose_service_action",
        "atlas_propose_proxmox_guest_action",
    }


    tool = tools[
        "atlas_propose_container_action"
    ]

    assert (
        tool.annotations
        is not None
    )

    assert (
        tool.annotations.read_only_hint
        is False
    )

    assert (
        tool.annotations.open_world_hint
        is False
    )


def test_operator_mcp_proposes_but_does_not_execute():

    fake = FakeProposalService()

    server = build_operator_server(
        proposal_service=fake
    )

    result = run(
        call(
            server,
            "atlas_propose_container_action",
            {
                "action":
                    "restart",

                "target":
                    "flaresolverr",
            },
        )
    )

    assert (
        result.is_error
        is False
    )

    data = (
        result
        .structured_content[
            "data"
        ]
    )

    assert (
        data["status"]
        == "PENDING_APPROVAL"
    )

    assert (
        data["requires_approval"]
        is True
    )

    assert (
        data["execution_allowed"]
        is False
    )

    assert fake.calls == [
        {
            "action":
                "restart",

            "target":
                "flaresolverr",
        }
    ]


def test_operator_mcp_has_no_direct_execution_tools():

    fake = FakeProposalService()

    server = build_operator_server(
        proposal_service=fake
    )

    result = run(
        list_tools(
            server
        )
    )

    names = {
        tool.name.lower()
        for tool in result.tools
    }

    forbidden = (
        "approve",
        "execute",
        "shell",
        "exec",
        "delete",
        "stop",
    )

    for token in forbidden:

        assert not any(
            token in name
            for name in names
        )


def test_operator_mcp_proposes_service_but_does_not_execute():

    fake = FakeProposalService()

    server = build_operator_server(
        proposal_service=fake
    )

    result = run(
        call(
            server,
            "atlas_propose_service_action",
            {
                "action":
                    "restart",

                "target":
                    "atlas-collector.service",
            },
        )
    )

    assert (
        result.is_error
        is False
    )

    data = (
        result
        .structured_content[
            "data"
        ]
    )

    assert (
        data["status"]
        == "PENDING_APPROVAL"
    )

    assert (
        data["resource_type"]
        == "service"
    )

    assert (
        data["requires_approval"]
        is True
    )

    assert (
        data["execution_allowed"]
        is False
    )

    assert fake.calls == [
        {
            "action":
                "restart",

            "target":
                "atlas-collector.service",
        }
    ]



def test_operator_mcp_proposes_vm_but_does_not_execute():

    fake = FakeProposalService()

    server = build_operator_server(
        proposal_service=fake
    )

    result = run(
        call(
            server,
            "atlas_propose_proxmox_guest_action",
            {
                "resource_type": "vm",
                "action": "restart",
                "target": "200",
            },
        )
    )

    assert result.is_error is False

    data = result.structured_content[
        "data"
    ]

    assert data["status"] == "PENDING_APPROVAL"
    assert data["resource_type"] == "vm"
    assert data["requires_approval"] is True
    assert data["execution_allowed"] is False

    assert fake.calls == [
        {
            "resource_type": "vm",
            "action": "restart",
            "target": "200",
        }
    ]
