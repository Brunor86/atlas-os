import pytest
from pydantic import ValidationError

from atlas.services.ai.operator.execution import (
    OperatorExecution,
    OperatorExecutionStatus,
)


def make_execution():
    return OperatorExecution(
        execution_id="exec-001",
        task="diagnose",
    )


def test_execution_starts_created():

    execution = make_execution()

    assert execution.status == OperatorExecutionStatus.CREATED
    assert execution.model is None
    assert execution.completed_at is None
    assert execution.error is None


def test_execution_supports_executing_state():

    execution = make_execution()

    execution.status = OperatorExecutionStatus.EXECUTING

    assert execution.status == OperatorExecutionStatus.EXECUTING


def test_execution_supports_completed_state():

    execution = make_execution()

    execution.status = OperatorExecutionStatus.EXECUTING
    execution.status = OperatorExecutionStatus.COMPLETED

    assert execution.status == OperatorExecutionStatus.COMPLETED


def test_execution_supports_failed_state():

    execution = make_execution()

    execution.status = OperatorExecutionStatus.EXECUTING
    execution.status = OperatorExecutionStatus.FAILED
    execution.error = "provider unavailable"

    assert execution.status == OperatorExecutionStatus.FAILED
    assert execution.error == "provider unavailable"


def test_execution_rejects_unknown_fields():

    with pytest.raises(ValidationError):

        OperatorExecution(
            execution_id="exec-001",
            task="diagnose",
            unexpected="value",
        )


def test_execution_assignment_is_validated():

    execution = make_execution()

    with pytest.raises(ValidationError):

        execution.execution_id = ""


def test_execution_serializes_status():

    execution = make_execution()

    execution.status = OperatorExecutionStatus.EXECUTING

    dumped = execution.model_dump()

    assert dumped["status"] == "executing"
