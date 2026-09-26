from types import SimpleNamespace

from atlas.mcp.operator_server import (
    OperatorProposalService,
)

from atlas.services.intelligence.execution.validators import (
    ActionValidator,
)

from atlas.services.intelligence.safety.service import (
    ActionSafetyService,
)


class FakeProxmox:

    def __init__(self):

        self.calls = []


    def resolve_guest(
        self,
        vmid,
        expected_type=None,
    ):

        self.calls.append(
            {
                "vmid": vmid,
                "expected_type": expected_type,
            }
        )

        guests = {
            200: SimpleNamespace(
                vmid=200,
                name="atlas-ai",
                type="qemu",
                node="atlas",
                status="running",
            ),

            103: SimpleNamespace(
                vmid=103,
                name="olivasat",
                type="lxc",
                node="atlas",
                status="running",
            ),

            300: SimpleNamespace(
                vmid=300,
                name="atlas-windows",
                type="qemu",
                node="atlas",
                status="stopped",
            ),
        }

        if vmid not in guests:

            raise LookupError(
                f"Proxmox guest VMID {vmid} not found"
            )

        guest = guests[
            vmid
        ]

        if (
            expected_type is not None
            and guest.type != expected_type
        ):

            raise ValueError(
                f"Proxmox VMID {vmid} "
                f"is {guest.type}, "
                f"not {expected_type}"
            )

        return guest


class FakeApproval:

    def __init__(self):

        self.requests = []


    def request(
        self,
        action,
    ):

        self.requests.append(
            action
        )

        return {
            "id": "ACTION-PROXMOX-TEST",
            **action.__dict__,
        }


def service():

    proposer = object.__new__(
        OperatorProposalService
    )

    proposer.proxmox = FakeProxmox()
    proposer.safety = ActionSafetyService()
    proposer.approval = FakeApproval()

    return proposer


def test_vm_restart_proposal_is_pending_only():

    proposer = service()

    result = proposer.propose_proxmox_guest_action(
        resource_type="vm",
        action="restart",
        target="200",
    )

    assert result["status"] == "PENDING_APPROVAL"
    assert result["resource_type"] == "vm"

    assert result["guest"] == {
        "vmid": 200,
        "name": "atlas-ai",
        "node": "atlas",
        "proxmox_type": "qemu",
        "status": "running",
    }

    assert result["safety"]["risk"] == "MEDIUM"
    assert result["requires_approval"] is True
    assert result["execution_allowed"] is False

    assert proposer.proxmox.calls == [
        {
            "vmid": 200,
            "expected_type": "qemu",
        }
    ]

    safe_action = (
        proposer
        .approval
        .requests[0]
    )

    assert safe_action.action == "restart vm"
    assert safe_action.target == "200"



def test_lxc_restart_proposal_is_pending_only():

    proposer = service()

    result = (
        proposer
        .propose_proxmox_guest_action(
            resource_type="lxc",
            action="restart",
            target="103",
        )
    )

    assert (
        result["status"]
        == "PENDING_APPROVAL"
    )

    assert (
        result["resource_type"]
        == "lxc"
    )

    assert result["guest"] == {
        "vmid": 103,
        "name": "olivasat",
        "node": "atlas",
        "proxmox_type": "lxc",
        "status": "running",
    }

    assert (
        result["requires_approval"]
        is True
    )

    assert (
        result["execution_allowed"]
        is False
    )

    assert proposer.proxmox.calls == [
        {
            "vmid": 103,
            "expected_type": "lxc",
        }
    ]

    assert len(
        proposer.approval.requests
    ) == 1

    safe_action = (
        proposer
        .approval
        .requests[0]
    )

    assert (
        safe_action.action
        == "restart lxc"
    )

    assert (
        safe_action.target
        == "103"
    )

def test_lxc_stop_is_high_risk_pending_only():

    proposer = service()

    result = proposer.propose_proxmox_guest_action(
        resource_type="lxc",
        action="stop",
        target="103",
    )

    assert result["status"] == "PENDING_APPROVAL"
    assert result["resource_type"] == "lxc"
    assert result["safety"]["risk"] == "HIGH"
    assert result["execution_allowed"] is False


def test_restart_stopped_vm_is_blocked():

    proposer = service()

    result = proposer.propose_proxmox_guest_action(
        resource_type="vm",
        action="restart",
        target="300",
    )

    assert result["status"] == "BLOCKED"

    assert (
        "use action='start'"
        in result["reason"]
    )

    assert proposer.approval.requests == []


def test_wrong_guest_type_is_blocked():

    proposer = service()

    result = proposer.propose_proxmox_guest_action(
        resource_type="lxc",
        action="restart",
        target="200",
    )

    assert result["status"] == "BLOCKED"

    assert (
        "is qemu, not lxc"
        in result["reason"]
    )

    assert proposer.approval.requests == []


def test_action_policy_allows_vm_actions_and_restart_lxc():

    allowed = set(
        ActionValidator.ALLOWED_ACTIONS
    )

    assert "start vm" in allowed
    assert "stop vm" in allowed
    assert "restart vm" in allowed
    assert "restart lxc" in allowed

    assert "start lxc" in allowed
    assert "stop lxc" in allowed
