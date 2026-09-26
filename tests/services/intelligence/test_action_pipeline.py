from atlas.models.action_plan import ActionPlan
from atlas.services.intelligence.action.builder import SafeActionBuilder
from atlas.services.intelligence.approval.service import (
    ActionApprovalService,
)
from atlas.services.intelligence.executor.service import (
    ActionExecutorService,
)


class FakeActionRepository:

    def __init__(self):
        self.actions = {}
        self.history = []
        self.learning_records = []
        self.execution_claims = set()

    def save_action_request(self, action):
        self.actions[action["id"]] = dict(action)

    def get_action_request(self, action_id):
        action = self.actions.get(action_id)
        return dict(action) if action else None

    def update_action_status(self, action_id, status, user):
        action = self.actions[action_id]

        action["status"] = status
        action["approved_by"] = user
        action["approved_at"] = "TEST"

        return {
            "id": action_id,
            "status": status,
            "approved_by": user,
        }

    def get_pending_actions(self):
        return [
            action
            for action in self.actions.values()
            if action["status"] == "PENDING_APPROVAL"
        ]

    def save_action_history(self, execution):
        self.history.append(dict(execution))

    def mark_action_executed(self, action_id):
        action = self.actions.get(action_id)

        if not action:
            return None

        action["status"] = "EXECUTED"

        return {
            "id": action_id,
            "status": "EXECUTED",
        }

    def get_action_history(self):
        return list(self.history)

    def claim_action_execution(self, approval_id):
        action = self.actions.get(approval_id)
        if (
            not action
            or action["status"] != "APPROVED"
            or approval_id in self.execution_claims
            or self.has_action_been_executed(approval_id)
        ):
            return False
        self.execution_claims.add(approval_id)
        return True

    def has_action_been_executed(self, approval_id):
        return any(
            record.get("approval_id") == approval_id
            for record in self.history
        )

    def save_learning(self, record):
        self.learning_records.append(record)


class FakeLifecycleRepository:

    def __init__(self):
        self.events = []

    def save(self, event):
        self.events.append(dict(event))

    def get_by_incident(self, incident_id):
        return [
            event
            for event in self.events
            if event["incident_id"] == incident_id
        ]


class FakeDockerHandler:

    def __init__(self):
        self.calls = []

    def restart_container(self, container):
        self.calls.append(container)

        return {
            "status": "SUCCESS",
            "result": f"fake restart: {container}",
            "evidence": [
                "fake docker restart executed",
                "fake container running verification passed",
            ],
        }


class FakeLearningRepository:

    def __init__(self):
        self.records = []

    def save_learning_record(self, record):
        self.records.append(record)


def test_action_pipeline_end_to_end():

    action_repository = FakeActionRepository()
    lifecycle_repository = FakeLifecycleRepository()

    approval = ActionApprovalService(
        action_repository=action_repository,
        lifecycle_repository=lifecycle_repository,
    )

    executor = ActionExecutorService(
        repository=action_repository,
        learning_repository=action_repository,
    )

    fake_docker = FakeDockerHandler()
    executor.execution.docker = fake_docker

    plan = ActionPlan(
        action="restart container",
        target="jellyseerr",
        incident_id="INC-PIPELINE-TEST",
        reason=[
            "DNS failure detected",
        ],
        evidence=[
            {
                "source": "docker",
                "type": "dns",
                "value": "resolution failed",
            }
        ],
        risk="LOW",
        prerequisites=[
            "verify container is running",
        ],
        rollback="docker start jellyseerr",
        confidence=0.95,
    )

    safe_action = SafeActionBuilder().build(
        plan.to_dict()
    )

    assert safe_action is not None
    assert safe_action.action == "restart container"
    assert safe_action.target == "jellyseerr"
    assert safe_action.incident_id == "INC-PIPELINE-TEST"
    assert safe_action.status == "PENDING_APPROVAL"

    request = approval.request(safe_action)

    assert request["status"] == "PENDING_APPROVAL"
    assert request["action"] == "restart container"
    assert request["target"] == "jellyseerr"

    pending = action_repository.get_action_request(
        request["id"]
    )

    assert pending["status"] == "PENDING_APPROVAL"

    lifecycle_states = [
        event["state"]
        for event in lifecycle_repository.events
    ]

    assert "PENDING_APPROVAL" in lifecycle_states

    blocked = executor.execute(request)

    assert blocked["status"] == "BLOCKED"
    assert blocked["approval_id"] == request["id"]

    approved = approval.approve(
        request["id"],
        user="TEST_OPERATOR",
    )

    assert approved["status"] == "APPROVED"
    assert approved["approved_by"] == "TEST_OPERATOR"

    approved_request = (
        action_repository.get_action_request(
            request["id"]
        )
    )

    assert approved_request["status"] == "APPROVED"

    lifecycle_states = [
        event["state"]
        for event in lifecycle_repository.events
    ]

    assert lifecycle_states[-1] == "APPROVED"

    execution = executor.execute(
        approved_request
    )

    assert execution.status == "SUCCESS"
    assert execution.action == "restart container"
    assert execution.target == "jellyseerr"
    assert execution.approval_id == request["id"]

    assert fake_docker.calls == [
        "jellyseerr",
    ]

    assert execution.evidence
    assert (
        "fake docker restart executed"
        in execution.evidence
    )

    assert len(action_repository.history) == 1

    history = action_repository.history[0]

    assert history["approval_id"] == request["id"]

    assert len(action_repository.learning_records) == 1

    learning = action_repository.learning_records[0]

    assert learning.incident_id == "INC-PIPELINE-TEST"
    assert learning.action == "restart container"
    assert learning.result == "SUCCESS"
    assert learning.resolution == "fake restart: jellyseerr"
    assert history["action"] == "restart container"
    assert history["target"] == "jellyseerr"
    assert history["status"] == "SUCCESS"


def test_executor_rejects_fabricated_approval():
    action_repository = FakeActionRepository()

    executor = ActionExecutorService(
        repository=action_repository,
        learning_repository=action_repository,
    )

    fake_docker = FakeDockerHandler()
    executor.execution.docker = fake_docker

    result = executor.execute({
        "id": "fabricated-approval",
        "action": "restart container",
        "target": "jellyseerr",
        "status": "APPROVED",
        "incident_id": "INC-FABRICATED",
    })

    assert result["status"] == "BLOCKED"
    assert result["approval_id"] == "fabricated-approval"


def test_executor_rejects_replay_of_same_approval():
    action_repository = FakeActionRepository()
    lifecycle_repository = FakeLifecycleRepository()

    approval = ActionApprovalService(
        action_repository=action_repository,
        lifecycle_repository=lifecycle_repository,
    )

    executor = ActionExecutorService(
        repository=action_repository,
        learning_repository=action_repository,
    )

    fake_docker = FakeDockerHandler()
    executor.execution.docker = fake_docker

    plan = ActionPlan(
        action="restart container",
        target="jellyseerr",
        incident_id="INC-REPLAY-TEST",
        risk="LOW",
        rollback="docker start jellyseerr",
    )

    safe_action = SafeActionBuilder().build(
        plan.to_dict()
    )

    request = approval.request(safe_action)

    approval.approve(
        request["id"],
        user="TEST_OPERATOR",
    )

    approved_request = (
        action_repository.get_action_request(
            request["id"]
        )
    )

    first = executor.execute(
        approved_request
    )

    assert first.status == "SUCCESS"

    second = executor.execute(
        approved_request
    )

    assert second["status"] == "BLOCKED"
    assert second["approval_id"] == request["id"]

def test_executor_rejects_approval_with_modified_target():
    action_repository = FakeActionRepository()
    lifecycle_repository = FakeLifecycleRepository()

    approval = ActionApprovalService(
        action_repository=action_repository,
        lifecycle_repository=lifecycle_repository,
    )

    executor = ActionExecutorService(
        repository=action_repository,
        learning_repository=action_repository,
    )

    plan = ActionPlan(
        action="restart container",
        target="jellyseerr",
        incident_id="INC-TAMPER-TEST",
        risk="LOW",
        rollback="docker start jellyseerr",
    )

    safe_action = SafeActionBuilder().build(
        plan.to_dict()
    )

    request = approval.request(
        safe_action
    )

    approval.approve(
        request["id"],
        user="TEST_OPERATOR",
    )

    tampered = dict(request)

    tampered["status"] = "APPROVED"
    tampered["target"] = "postgres"

    result = executor.execute(
        tampered
    )

    assert result["status"] == "BLOCKED"
    assert result["approval_id"] == request["id"]
    assert "target" in result["reason"][0]


def test_executor_uses_persisted_approval():
    action_repository = FakeActionRepository()
    lifecycle_repository = FakeLifecycleRepository()

    approval = ActionApprovalService(
        action_repository=action_repository,
        lifecycle_repository=lifecycle_repository,
    )

    executor = ActionExecutorService(
        repository=action_repository,
        learning_repository=action_repository,
    )

    fake_docker = FakeDockerHandler()
    executor.execution.docker = fake_docker

    plan = ActionPlan(
        action="restart container",
        target="jellyseerr",
        incident_id="INC-PERSISTED-TEST",
        risk="LOW",
        rollback="docker start jellyseerr",
    )

    safe_action = SafeActionBuilder().build(
        plan.to_dict()
    )

    request = approval.request(
        safe_action
    )

    approval.approve(
        request["id"],
        user="TEST_OPERATOR",
    )

    caller_payload = {
        "id": request["id"],
        "status": "APPROVED",
        "incident_id": request["incident_id"],
        "action": request["action"],
        "target": request["target"],
    }

    result = executor.execute(
        caller_payload
    )

    assert result.status == "SUCCESS"
    assert result.approval_id == request["id"]
    assert result.target == "jellyseerr"



def test_successful_execution_does_not_mark_incident_resolved():
    action_repository = FakeActionRepository()
    lifecycle_repository = FakeLifecycleRepository()

    approval = ActionApprovalService(
        action_repository=action_repository,
        lifecycle_repository=lifecycle_repository,
    )

    executor = ActionExecutorService(
        repository=action_repository,
        learning_repository=action_repository,
    )

    fake_docker = FakeDockerHandler()
    executor.execution.docker = fake_docker

    plan = ActionPlan(
        action="restart container",
        target="jellyseerr",
        incident_id="INC-LIFECYCLE-CONTRACT",
        risk="LOW",
        rollback="docker start jellyseerr",
    )

    safe_action = SafeActionBuilder().build(
        plan.to_dict()
    )

    request = approval.request(
        safe_action
    )

    approval.approve(
        request["id"],
        user="TEST_OPERATOR",
    )

    execution = executor.execute(
        action_repository.get_action_request(
            request["id"]
        )
    )

    assert execution.status == "SUCCESS"

    persisted = action_repository.get_action_request(
        request["id"]
    )

    assert persisted["status"] == "EXECUTED"

    lifecycle = lifecycle_repository.get_by_incident(
        "INC-LIFECYCLE-CONTRACT"
    )

    states = [
        event["state"]
        for event in lifecycle
    ]

    assert states == [
        "PENDING_APPROVAL",
        "APPROVED",
    ]

    assert "RESOLVED" not in states

def test_successful_execution_persists_executed_status():
    action_repository = FakeActionRepository()
    lifecycle_repository = FakeLifecycleRepository()

    approval = ActionApprovalService(
        action_repository=action_repository,
        lifecycle_repository=lifecycle_repository,
    )

    executor = ActionExecutorService(
        repository=action_repository,
        learning_repository=action_repository,
    )

    fake_docker = FakeDockerHandler()
    executor.execution.docker = fake_docker

    plan = ActionPlan(
        action="restart container",
        target="jellyseerr",
        incident_id="INC-EXECUTED-STATUS",
        risk="LOW",
        rollback="docker start jellyseerr",
    )

    safe_action = SafeActionBuilder().build(
        plan.to_dict()
    )

    request = approval.request(
        safe_action
    )

    approval.approve(
        request["id"],
        user="TEST_OPERATOR",
    )

    execution = executor.execute(
        action_repository.get_action_request(
            request["id"]
        )
    )

    assert execution.status == "SUCCESS"

    persisted = action_repository.get_action_request(
        request["id"]
    )

    assert persisted["status"] == "EXECUTED"

def test_safety_blocked_action_never_reaches_approval_or_execution():

    from atlas.services.intelligence.safety.service import (
        ActionSafetyService,
    )

    class Incident:
        incident_id = "INC-SAFETY-BLOCK"
        asset = "/dev/sdb"
        recommendation = {
            "action": "restart",
            "evidence": [
                {
                    "source": "storage",
                    "type": "health",
                    "value": "failure",
                }
            ],
        }
        diagnosis = {
            "type": "STORAGE_HEALTH_FAILURE",
            "category": "STORAGE",
            "confidence": 0.99,
        }

    result = ActionSafetyService().evaluate(Incident())

    assert result["status"] == "BLOCKED"
    assert result["requires_approval"] is False
    assert result["target"] == "/dev/sdb"
    assert result["incident_id"] == "INC-SAFETY-BLOCK"


def test_blocked_action_is_not_pending_approval():

    from atlas.services.intelligence.safety.service import (
        ActionSafetyService,
    )

    class Incident:
        incident_id = "INC-SAFETY-BLOCK-2"
        asset = "jellyseerr"
        recommendation = {
            "action": "unsupported destructive action",
        }
        diagnosis = {
            "type": "UNKNOWN",
            "category": "UNKNOWN",
            "confidence": 0.50,
        }

    result = ActionSafetyService().evaluate(Incident())

    assert result["status"] == "BLOCKED"
    assert result["requires_approval"] is False
    assert result["risk"] == "UNKNOWN"

def test_blocked_safety_persists_blocked_lifecycle_state():

    from atlas.services.intelligence.safety.service import (
        ActionSafetyService,
    )

    from atlas.services.incidents.lifecycle import (
        IncidentLifecycle,
    )

    class Repository:

        def __init__(self):
            self.events = []

        def save(self, event):
            self.events.append(dict(event))

    class Incident:
        incident_id = "INC-LIFECYCLE-BLOCKED"
        asset = "/dev/sdb"
        recommendation = {
            "action": "restart",
        }
        diagnosis = {
            "type": "STORAGE_HEALTH_FAILURE",
            "category": "STORAGE",
            "confidence": 0.99,
        }

    incident = Incident()

    safety = ActionSafetyService().evaluate(incident)

    assert safety["status"] == "BLOCKED"

    repository = Repository()
    lifecycle = IncidentLifecycle(repository)

    lifecycle.transition(
        incident,
        "RECOMMENDED",
        "Operational recommendation generated",
    )

    if safety["status"] == "BLOCKED":

        lifecycle.transition(
            incident,
            "BLOCKED",
            "Action blocked by safety gate",
        )

    states = [
        event["state"]
        for event in repository.events
    ]

    assert states == [
        "RECOMMENDED",
        "BLOCKED",
    ]

    assert "APPROVED" not in states
    assert "EXECUTING" not in states

    blocked = repository.events[-1]

    assert blocked["incident_id"] == (
        "INC-LIFECYCLE-BLOCKED"
    )

    assert blocked["actor"] == "ATLAS"
    assert blocked["detail"] == (
        "Action blocked by safety gate"
    )

# ATLAS v0.125 · FAIL-CLOSED EXECUTION DISPATCH


class FailClosedExecutionRepository:

    def __init__(
        self,
    ):

        self.history = []
        self.executed = []


    def save_action_history(
        self,
        record,
    ):

        self.history.append(
            record
        )


    def mark_action_executed(
        self,
        approval_id,
    ):

        self.executed.append(
            approval_id
        )


def test_allowed_but_unrouted_action_fails_closed():

    from atlas.services.intelligence.execution.service import (
        ActionExecutionService,
    )

    repository = (
        FailClosedExecutionRepository()
    )

    executor = (
        ActionExecutionService(
            repository=repository,
        )
    )

    learning_calls = []

    def unexpected_learning(
        **kwargs,
    ):

        learning_calls.append(
            kwargs
        )

    executor.learning.learn = (
        unexpected_learning
    )

    result = executor.execute(
        {
            "id":
                "approval-fail-closed",

            "incident_id":
                "incident-fail-closed",

            "action":
                "inspect stopped containers",

            "target":
                "docker",

            "status":
                "APPROVED",
        }
    )

    assert result.status == "REJECTED"

    assert (
        "no execution handler"
        in result.result
    )

    assert result.evidence == [
        "no explicit execution route",
    ]

    assert repository.executed == []

    assert learning_calls == []

    assert len(
        repository.history
    ) == 1

    assert (
        repository.history[0][
            "status"
        ]
        == "REJECTED"
    )


def test_fail_closed_default_does_not_break_explicit_route():

    from atlas.services.intelligence.execution.service import (
        ActionExecutionService,
    )

    class FakeDocker:

        def start_container(
            self,
            target,
        ):

            return {
                "status": "SUCCESS",
                "result": (
                    "fake start "
                    + str(target)
                ),
                "evidence": [
                    "explicit route executed",
                ],
            }

    executor = (
        ActionExecutionService()
    )

    executor.docker = (
        FakeDocker()
    )

    result = executor.execute(
        {
            "id":
                "approval-routed",

            "incident_id":
                "incident-routed",

            "action":
                "start container",

            "target":
                "synthetic-container",

            "status":
                "APPROVED",
        }
    )

    assert result.status == "SUCCESS"

    assert result.result == (
        "fake start synthetic-container"
    )

    assert result.evidence == [
        "explicit route executed",
    ]

# ATLAS v0.126 · EXECUTABLE CAPABILITY TRUTH


def test_execution_capability_truth_matches_real_routes():

    from atlas.services.intelligence.execution.service import (
        ActionExecutionService,
    )

    assert (
        ActionExecutionService
        .is_action_executable(
            "start container"
        )
        is True
    )

    assert (
        ActionExecutionService
        .is_action_executable(
            "restart service"
        )
        is True
    )

    assert (
        ActionExecutionService
        .is_action_executable(
            "restart vm"
        )
        is True
    )

    assert (
        ActionExecutionService
        .is_action_executable(
            "start lxc"
        )
        is True
    )

    assert (
        ActionExecutionService
        .is_action_executable(
            "stop lxc"
        )
        is True
    )

    assert (
        ActionExecutionService
        .is_action_executable(
            "inspect stopped containers"
        )
        is False
    )


def test_execution_capability_fails_closed_for_unknown_action():

    from atlas.services.intelligence.execution.service import (
        ActionExecutionService,
    )

    assert (
        ActionExecutionService
        .is_action_executable(
            "future allowed action"
        )
        is False
    )


def test_validator_drift_remains_rejected_without_route():

    from atlas.services.intelligence.execution.service import (
        ActionExecutionService,
    )

    from atlas.services.intelligence.execution.validators import (
        ActionValidator,
    )

    original = list(
        ActionValidator.ALLOWED_ACTIONS
    )

    try:

        ActionValidator.ALLOWED_ACTIONS = (
            original
            + [
                "future allowed action",
            ]
        )

        executor = (
            ActionExecutionService()
        )

        result = executor.execute(
            {
                "id":
                    "approval-future-drift",

                "incident_id":
                    "incident-future-drift",

                "action":
                    "future allowed action",

                "target":
                    "synthetic",

                "status":
                    "APPROVED",
            }
        )

        assert (
            result.status
            == "REJECTED"
        )

        assert (
            "no execution handler"
            in result.result
        )

    finally:

        ActionValidator.ALLOWED_ACTIONS = (
            original
        )
