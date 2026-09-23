import inspect
from types import SimpleNamespace

from atlas.models.noc import (
    NOCIncident,
    NOCStatus,
)
from atlas.services.noc.service import (
    NOCService,
)


class FakeProposalBridge:

    def __init__(
        self,
        result=None,
        error=None,
    ):
        self.result = (
            result
            or {}
        )
        self.error = error
        self.calls = []

    def propose(
        self,
        incident_id,
    ):
        self.calls.append(
            incident_id
        )

        if self.error:
            raise self.error

        return dict(
            self.result
        )


def test_noc_proposal_helper_never_enables_execution():

    service = NOCService.__new__(
        NOCService
    )

    service.action_proposals = (
        FakeProposalBridge(
            {
                "status":
                    "PENDING_APPROVAL",

                "incident_id":
                    "INC-0002",

                "created":
                    True,
            }
        )
    )

    incident = SimpleNamespace(
        incident_id="INC-0002",
        action_proposal={},
        approval_context={},
    )

    result = (
        service
        ._propose_incident_action(
            incident
        )
    )

    assert (
        service.action_proposals.calls
        == ["INC-0002"]
    )

    assert result[
        "status"
    ] == "PENDING_APPROVAL"

    assert result[
        "execution_allowed"
    ] is False

    assert incident.action_proposal == (
        result
    )

    assert incident.approval_context == (
        result
    )


def test_noc_proposal_helper_fails_closed():

    service = NOCService.__new__(
        NOCService
    )

    service.action_proposals = (
        FakeProposalBridge(
            error=RuntimeError(
                "proposal unavailable"
            )
        )
    )

    incident = SimpleNamespace(
        incident_id="INC-0002",
        action_proposal={},
        approval_context={},
    )

    result = (
        service
        ._propose_incident_action(
            incident
        )
    )

    assert result[
        "status"
    ] == "ERROR"

    assert result[
        "execution_allowed"
    ] is False

    assert incident.action_proposal == (
        result
    )


def test_noc_generate_has_no_direct_approval_or_execution():

    source = inspect.getsource(
        NOCService.generate
    )

    assert (
        "self.executor.execute("
        not in source
    )

    assert (
        "self.approval.request("
        not in source
    )

    assert (
        "AUTO_APPROVED"
        not in source
    )

    assert (
        "self._propose_incident_action("
        in source
    )


def test_noc_status_serializes_action_proposal():

    incident = NOCIncident(
        name="service_degradation",
        confidence=0.9,
        reason="test",
        incident_id="INC-0002",
    )

    incident.action_proposal = {
        "status":
            "DECISION_HELD",

        "decision":
            "REJECTED",

        "execution_allowed":
            False,
    }

    status = NOCStatus(
        status="WARNING",
        score=30,
        priority="MEDIUM",
        summary="test",
        incidents=[
            incident
        ],
    )

    serialized = (
        status.to_dict()
    )

    proposal = (
        serialized[
            "incidents"
        ][0][
            "action_proposal"
        ]
    )

    assert proposal[
        "status"
    ] == "DECISION_HELD"

    assert proposal[
        "decision"
    ] == "REJECTED"

    assert proposal[
        "execution_allowed"
    ] is False
