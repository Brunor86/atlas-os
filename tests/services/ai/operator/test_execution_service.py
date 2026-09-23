import pytest

from atlas.services.ai.models import (
    AIRequest,
    LLMResponse,
)
from atlas.services.ai.operator.execution import (
    OperatorExecutionStatus,
)
from atlas.services.ai.operator.execution_service import (
    OperatorExecutionService,
)
from atlas.services.ai.operator.models import (
    AIModelCapabilities,
    AIModelProfile,
)


class FakeOperator:

    def __init__(self):
        self.profile = AIModelProfile(
            name="qwen_reasoning",
            provider="ollama",
            provider_model="qwen2.5:7b",
            capabilities=AIModelCapabilities(
                reasoning=True,
            ),
        )

    def select(self, task, runtime):
        return self.profile


def make_request():

    return AIRequest(
        task="diagnosis",
        user_prompt="Diagnose the incident",
    )


def make_response():

    return LLMResponse(
        model="qwen_reasoning",
        provider="ollama",
        content="Diagnosis completed",
    )


def test_create_starts_execution_in_created_state():

    service = OperatorExecutionService(
        FakeOperator()
    )

    execution = service.create(
        make_request()
    )

    assert execution.status == (
        OperatorExecutionStatus.CREATED
    )

    assert execution.execution_id
    assert execution.task == "diagnosis"
    assert execution.completed_at is None


def test_select_model_updates_execution():

    service = OperatorExecutionService(
        FakeOperator()
    )

    request = make_request()

    execution = service.create(request)

    model = service.select_model(
        execution,
        request,
        runtime=object(),
    )

    assert model is not None

    assert execution.status == (
        OperatorExecutionStatus.MODEL_SELECTED
    )

    assert execution.model == "qwen_reasoning"
    assert execution.provider == "ollama"
    assert execution.provider_model == "qwen2.5:7b"


def test_execute_completes_execution():

    service = OperatorExecutionService(
        FakeOperator()
    )

    request = make_request()

    execution = service.create(request)

    service.select_model(
        execution,
        request,
        runtime=object(),
    )

    response = service.execute(
        execution,
        request,
        executor=lambda _: make_response(),
    )

    assert response.content == "Diagnosis completed"

    assert execution.status == (
        OperatorExecutionStatus.COMPLETED
    )

    assert execution.completed_at is not None
    assert execution.error is None


def test_execute_rejects_execution_without_model():

    service = OperatorExecutionService(
        FakeOperator()
    )

    request = make_request()

    execution = service.create(request)

    with pytest.raises(RuntimeError):

        service.execute(
            execution,
            request,
            executor=lambda _: make_response(),
        )

    assert execution.status == (
        OperatorExecutionStatus.CREATED
    )


def test_executor_exception_marks_execution_failed():

    service = OperatorExecutionService(
        FakeOperator()
    )

    request = make_request()

    execution = service.create(request)

    service.select_model(
        execution,
        request,
        runtime=object(),
    )

    def failing_executor(_):
        raise RuntimeError(
            "ollama unavailable"
        )

    with pytest.raises(RuntimeError):

        service.execute(
            execution,
            request,
            executor=failing_executor,
        )

    assert execution.status == (
        OperatorExecutionStatus.FAILED
    )

    assert execution.error == (
        "ollama unavailable"
    )

    assert execution.completed_at is not None


def test_response_error_marks_execution_failed():

    service = OperatorExecutionService(
        FakeOperator()
    )

    request = make_request()

    execution = service.create(request)

    service.select_model(
        execution,
        request,
        runtime=object(),
    )

    response = LLMResponse(
        model="qwen_reasoning",
        provider="ollama",
        content="",
        metadata={
            "error": "provider failed",
        },
    )

    result = service.execute(
        execution,
        request,
        executor=lambda _: response,
    )

    assert result is response

    assert execution.status == (
        OperatorExecutionStatus.FAILED
    )

    assert execution.error == (
        "provider failed"
    )

    assert execution.completed_at is not None


def test_create_generates_unique_execution_ids():

    service = OperatorExecutionService(
        FakeOperator()
    )

    first = service.create(
        make_request()
    )

    second = service.create(
        make_request()
    )

    assert first.execution_id != (
        second.execution_id
    )
