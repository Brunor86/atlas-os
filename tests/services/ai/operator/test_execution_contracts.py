import pytest
from pydantic import ValidationError

from atlas.services.ai.operator.execution import (
    OperatorExecution,
    OperatorExecutionStatus,
)


def test_execution_is_pydantic_contract():

    execution = OperatorExecution(
        execution_id="exec-001",
        task="diagnosis",
    )

    assert execution.execution_id == "exec-001"
    assert execution.task == "diagnosis"
    assert execution.status == OperatorExecutionStatus.CREATED
    assert execution.model is None


def test_execution_has_utc_start_timestamp():

    execution = OperatorExecution(
        execution_id="exec-001",
        task="diagnosis",
    )

    assert execution.started_at.tzinfo is not None
    assert execution.started_at.utcoffset() is not None


def test_execution_accepts_model_selection():

    execution = OperatorExecution(
        execution_id="exec-001",
        task="diagnosis",
        status=OperatorExecutionStatus.MODEL_SELECTED,
        model="qwen_reasoning",
        provider="ollama",
        provider_model="qwen2.5:7b",
    )

    assert execution.model == "qwen_reasoning"
    assert execution.provider == "ollama"
    assert execution.provider_model == "qwen2.5:7b"


def test_execution_rejects_empty_id():

    with pytest.raises(ValidationError):

        OperatorExecution(
            execution_id="",
            task="diagnosis",
        )


def test_execution_rejects_empty_task():

    with pytest.raises(ValidationError):

        OperatorExecution(
            execution_id="exec-001",
            task="",
        )


def test_execution_rejects_unknown_fields():

    with pytest.raises(ValidationError):

        OperatorExecution(
            execution_id="exec-001",
            task="diagnosis",
            unexpected="value",
        )


def test_execution_assignment_is_validated():

    execution = OperatorExecution(
        execution_id="exec-001",
        task="diagnosis",
    )

    execution.status = OperatorExecutionStatus.SELECTING_MODEL

    assert execution.status == (
        OperatorExecutionStatus.SELECTING_MODEL
    )

    with pytest.raises(ValidationError):
        execution.execution_id = ""


def test_execution_serializes_cleanly():

    execution = OperatorExecution(
        execution_id="exec-001",
        task="diagnosis",
        status=OperatorExecutionStatus.MODEL_SELECTED,
        model="qwen_reasoning",
        provider="ollama",
        provider_model="qwen2.5:7b",
    )

    dumped = execution.model_dump()

    assert dumped["execution_id"] == "exec-001"
    assert dumped["task"] == "diagnosis"
    assert dumped["status"] == "model_selected"
    assert dumped["model"] == "qwen_reasoning"
