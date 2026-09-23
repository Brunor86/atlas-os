from atlas.mcp.operator_client import (
    MCPOperatorClient,
)
from atlas.mcp.operator_server import (
    build_operator_server,
)


class FakeProposalService:

    def __init__(
        self,
    ):

        self.calls = []


    def propose_container_action(
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

            "action_request": {
                "id":
                    "ACTION-CLIENT-TEST",

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
                "id": "ACTION-PROXMOX-CLIENT-TEST",
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



def build_client(
    fake,
):

    return MCPOperatorClient(
        server_builder=(
            lambda: build_operator_server(
                proposal_service=fake
            )
        )
    )


def test_operator_client_exposes_only_proposal_capability():

    fake = FakeProposalService()

    client = build_client(
        fake
    )


    tools = (
        client.list_tools()
    )


    assert len(
        tools
    ) == 3


    assert (
        tools[0]["name"]
        == "atlas_propose_container_action"
    )

    assert (
        tools[0]["read_only"]
        is False
    )

    assert (
        tools[0]["requires_approval"]
        is True
    )


def test_operator_client_can_create_pending_proposal():

    fake = FakeProposalService()

    client = build_client(
        fake
    )


    result = (
        client.execute_tool(
            "atlas_propose_container_action",
            action="restart",
            target="flaresolverr",
        )
    )


    assert (
        result.success
        is True
    )

    assert (
        result.data["status"]
        == "PENDING_APPROVAL"
    )

    assert (
        result.data[
            "execution_allowed"
        ]
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


def test_operator_client_blocks_approval_tool():

    fake = FakeProposalService()

    client = build_client(
        fake
    )


    result = (
        client.execute_tool(
            "atlas_approve_action",
            action_id="ACTION-1",
        )
    )


    assert (
        result.success
        is False
    )

    assert (
        "Unauthorized"
        in result.error
    )

    assert fake.calls == []


def test_operator_client_blocks_execution_tool():

    fake = FakeProposalService()

    client = build_client(
        fake
    )


    result = (
        client.execute_tool(
            "atlas_execute_action",
            action_id="ACTION-1",
        )
    )


    assert (
        result.success
        is False
    )

    assert fake.calls == []


def test_operator_client_can_create_pending_service_proposal():

    fake = FakeProposalService()

    client = build_client(
        fake
    )

    result = (
        client.execute_tool(
            "atlas_propose_service_action",
            action="restart",
            target="atlas-collector.service",
        )
    )

    assert (
        result.success
        is True
    )

    assert (
        result.data["status"]
        == "PENDING_APPROVAL"
    )

    assert (
        result.data["resource_type"]
        == "service"
    )

    assert (
        result.data[
            "execution_allowed"
        ]
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



def test_operator_client_can_create_pending_vm_proposal():

    fake = FakeProposalService()

    client = build_client(
        fake
    )

    result = client.execute_tool(
        "atlas_propose_proxmox_guest_action",
        resource_type="vm",
        action="restart",
        target="200",
    )

    assert result.success is True
    assert result.data["status"] == "PENDING_APPROVAL"
    assert result.data["resource_type"] == "vm"
    assert result.data["execution_allowed"] is False

    assert fake.calls == [
        {
            "resource_type": "vm",
            "action": "restart",
            "target": "200",
        }
    ]
