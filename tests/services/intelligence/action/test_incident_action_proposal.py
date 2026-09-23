from atlas.services.intelligence.action.proposal import (
    IncidentActionProposalService,
)


class FakeOperator:

    def __init__(
        self,
        safety,
    ):

        self.safety = safety
        self.calls = []


    def analyze(
        self,
        incident_id,
    ):

        self.calls.append(
            incident_id
        )

        return {
            "incident": {
                "id": incident_id,
                "title": "test incident",
                "asset_id": "test-asset",
                "severity": "HIGH",
                "status": "OPEN",
                "evidence": [],
                "recommendations": [],
                "impact": [],
                "impact_intelligence": {},
                "root_cause": "",
                "diagnosis": "",
                "blast_radius": [],
                "suggested_actions": [],
            },
            "safety":
                dict(
                    self.safety
                )
        }


class FakeActionRepository:

    def __init__(
        self,
        pending=None,
    ):

        self.pending = list(
            pending
            or []
        )


    def get_pending_actions(
        self,
    ):

        return list(
            self.pending
        )


class FakeApproval:

    def __init__(
        self,
    ):

        self.requests = []


    def request(
        self,
        action,
        incident_fingerprint=None,
    ):

        self.requests.append(
            action
        )

        return {
            "id":
                "REQ-001",

            "incident_id":
                action.incident_id,

            "action":
                action.action,

            "target":
                action.target,

            "risk":
                action.risk,

            "rollback":
                action.rollback,

            "status":
                "PENDING_APPROVAL",
        }


def build_service(
    safety,
    pending=None,
):

    operator = FakeOperator(
        safety
    )

    actions = FakeActionRepository(
        pending
    )

    approval = FakeApproval()

    service = (
        IncidentActionProposalService(
            operator=operator,
            action_repository=actions,
            approval=approval,
        )
    )

    return (
        service,
        operator,
        approval,
    )


def pending_safety():

    return {
        "action":
            "restart service",

        "target":
            "atlas-collector.service",

        "incident_id":
            "INC-0007",

        "risk":
            "LOW",

        "requires_approval":
            True,

        "rollback":
            (
                "systemctl start "
                "atlas-collector.service"
            ),

        "status":
            "PENDING_APPROVAL",

        "evidence":
            [
                "collector unhealthy",
            ],
    }


def test_creates_persistent_action_proposal():

    (
        service,
        operator,
        approval,
    ) = build_service(
        pending_safety()
    )

    result = service.propose(
        "INC-0007"
    )

    assert result[
        "status"
    ] == "PENDING_APPROVAL"

    assert result[
        "created"
    ] is True

    assert result[
        "idempotent"
    ] is False

    assert operator.calls == [
        "INC-0007",
    ]

    assert len(
        approval.requests
    ) == 1

    action = approval.requests[0]

    assert action.incident_id == (
        "INC-0007"
    )

    assert action.action == (
        "restart service"
    )

    assert action.target == (
        "atlas-collector.service"
    )

    assert action.risk == "LOW"


def test_reuses_existing_pending_proposal():

    existing = (
        "REQ-EXISTING",
        "INC-0007",
        "restart service",
        "atlas-collector.service",
        "LOW",
        (
            "systemctl start "
            "atlas-collector.service"
        ),
        "PENDING_APPROVAL",
        "2026-09-11T08:00:00+00:00",
        None,
        None,
    )

    (
        service,
        _operator,
        approval,
    ) = build_service(
        pending_safety(),
        pending=[
            existing,
        ],
    )

    result = service.propose(
        "INC-0007"
    )

    assert result[
        "status"
    ] == "PENDING_APPROVAL"

    assert result[
        "created"
    ] is False

    assert result[
        "idempotent"
    ] is True

    assert (
        result[
            "action_request"
        ][
            "id"
        ]
        == "REQ-EXISTING"
    )

    assert approval.requests == []


def test_no_action_does_not_create_request():

    (
        service,
        _operator,
        approval,
    ) = build_service(
        {
            "status":
                "NO_ACTION",

            "reason":
                "no valid recommendation",

            "incident_id":
                "INC-0007",
        }
    )

    result = service.propose(
        "INC-0007"
    )

    assert result[
        "status"
    ] == "NO_ACTION"

    assert approval.requests == []


def test_blocked_action_does_not_create_request():

    (
        service,
        _operator,
        approval,
    ) = build_service(
        {
            "status":
                "BLOCKED",

            "reason":
                "safety policy blocked action",

            "incident_id":
                "INC-0007",

            "action":
                "restart service",

            "target":
                "atlas-web.service",
        }
    )

    result = service.propose(
        "INC-0007"
    )

    assert result[
        "status"
    ] == "BLOCKED"

    assert approval.requests == []


def test_non_approval_action_is_not_persisted():

    (
        service,
        _operator,
        approval,
    ) = build_service(
        {
            "status":
                "SAFE",

            "action":
                "inspect stopped containers",

            "target":
                "docker",

            "incident_id":
                "INC-0007",

            "requires_approval":
                False,
        }
    )

    result = service.propose(
        "INC-0007"
    )

    assert result[
        "status"
    ] == "NO_PROPOSAL"

    assert approval.requests == []


def test_missing_action_target_is_not_persisted():

    (
        service,
        _operator,
        approval,
    ) = build_service(
        {
            "status":
                "PENDING_APPROVAL",

            "incident_id":
                "INC-0007",

            "requires_approval":
                True,
        }
    )

    result = service.propose(
        "INC-0007"
    )

    assert result[
        "status"
    ] == "NO_PROPOSAL"

    assert approval.requests == []


def _fingerprint_for(
    incident,
):

    return (
        IncidentActionProposalService
        ._incident_fingerprint(
            incident
        )
    )


def test_same_rejected_decision_is_held():

    incident = {
        "id": "INC-0007",
        "title": "service_degradation",
        "asset_id": "collector",
        "severity": "HIGH",
        "status": "OPEN",
        "evidence": ["offline"],
        "recommendations": [],
        "impact": [],
        "impact_intelligence": {},
        "root_cause": "collector stopped",
        "diagnosis": "collector unavailable",
        "blast_radius": [],
        "suggested_actions": [],
    }

    fingerprint = _fingerprint_for(
        incident
    )

    class DecisionOperator(FakeOperator):

        def analyze(
            self,
            incident_id,
        ):
            self.calls.append(
                incident_id
            )

            return {
                "incident":
                    incident,

                "safety":
                    dict(
                        self.safety
                    ),
            }


    class DecisionRepository(
        FakeActionRepository
    ):

        def get_action_requests_by_incident(
            self,
            incident_id,
        ):
            return list(
                self.pending
            )


    operator = DecisionOperator(
        pending_safety()
    )

    actions = DecisionRepository(
        [
            {
                "id":
                    "REQ-REJECTED",

                "incident_id":
                    "INC-0007",

                "action":
                    "restart service",

                "target":
                    "atlas-collector.service",

                "risk":
                    "LOW",

                "rollback":
                    (
                        "systemctl start "
                        "atlas-collector.service"
                    ),

                "status":
                    "REJECTED",

                "incident_fingerprint":
                    fingerprint,
            }
        ]
    )

    approval = FakeApproval()

    service = (
        IncidentActionProposalService(
            operator=operator,
            action_repository=actions,
            approval=approval,
        )
    )

    result = service.propose(
        "INC-0007"
    )

    assert result[
        "status"
    ] == "DECISION_HELD"

    assert result[
        "decision"
    ] == "REJECTED"

    assert result[
        "created"
    ] is False

    assert approval.requests == []


def test_changed_incident_allows_new_proposal():

    old_incident = {
        "id": "INC-0007",
        "title": "service_degradation",
        "asset_id": "collector",
        "severity": "MEDIUM",
        "status": "OPEN",
        "evidence": ["offline"],
        "recommendations": [],
        "impact": [],
        "impact_intelligence": {},
        "root_cause": "collector stopped",
        "diagnosis": "collector unavailable",
        "blast_radius": [],
        "suggested_actions": [],
    }

    new_incident = dict(
        old_incident
    )

    new_incident[
        "severity"
    ] = "HIGH"

    old_fingerprint = (
        _fingerprint_for(
            old_incident
        )
    )

    class ChangedOperator(FakeOperator):

        def analyze(
            self,
            incident_id,
        ):
            self.calls.append(
                incident_id
            )

            return {
                "incident":
                    new_incident,

                "safety":
                    dict(
                        self.safety
                    ),
            }


    class ChangedRepository(
        FakeActionRepository
    ):

        def get_action_requests_by_incident(
            self,
            incident_id,
        ):
            return list(
                self.pending
            )


    operator = ChangedOperator(
        pending_safety()
    )

    actions = ChangedRepository(
        [
            {
                "id":
                    "REQ-OLD",

                "incident_id":
                    "INC-0007",

                "action":
                    "restart service",

                "target":
                    "atlas-collector.service",

                "risk":
                    "LOW",

                "rollback":
                    (
                        "systemctl start "
                        "atlas-collector.service"
                    ),

                "status":
                    "REJECTED",

                "incident_fingerprint":
                    old_fingerprint,
            }
        ]
    )

    approval = FakeApproval()

    service = (
        IncidentActionProposalService(
            operator=operator,
            action_repository=actions,
            approval=approval,
        )
    )

    result = service.propose(
        "INC-0007"
    )

    assert result[
        "status"
    ] == "PENDING_APPROVAL"

    assert result[
        "created"
    ] is True

    assert len(
        approval.requests
    ) == 1


def test_changed_incident_with_old_pending_fails_closed():

    old_incident = {
        "id": "INC-0007",
        "title": "service_degradation",
        "asset_id": "collector",
        "severity": "MEDIUM",
        "status": "OPEN",
        "evidence": ["offline"],
        "recommendations": [],
        "impact": [],
        "impact_intelligence": {},
        "root_cause": "collector stopped",
        "diagnosis": "collector unavailable",
        "blast_radius": [],
        "suggested_actions": [],
    }

    new_incident = dict(
        old_incident
    )

    new_incident[
        "severity"
    ] = "HIGH"

    old_fingerprint = (
        _fingerprint_for(
            old_incident
        )
    )

    class PendingOperator(FakeOperator):

        def analyze(
            self,
            incident_id,
        ):
            return {
                "incident":
                    new_incident,

                "safety":
                    dict(
                        self.safety
                    ),
            }


    class PendingRepository(
        FakeActionRepository
    ):

        def get_action_requests_by_incident(
            self,
            incident_id,
        ):
            return list(
                self.pending
            )


    actions = PendingRepository(
        [
            {
                "id":
                    "REQ-STALE",

                "incident_id":
                    "INC-0007",

                "action":
                    "restart service",

                "target":
                    "atlas-collector.service",

                "status":
                    "PENDING_APPROVAL",

                "incident_fingerprint":
                    old_fingerprint,
            }
        ]
    )

    approval = FakeApproval()

    service = (
        IncidentActionProposalService(
            operator=PendingOperator(
                pending_safety()
            ),
            action_repository=actions,
            approval=approval,
        )
    )

    result = service.propose(
        "INC-0007"
    )

    assert result[
        "status"
    ] == "STALE_PENDING"

    assert result[
        "created"
    ] is False

    assert approval.requests == []
