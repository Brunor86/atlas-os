from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

from atlas.services.ai.models import AIRequest, LLMResponse
from atlas.services.ai.operator.execution import (
    OperatorExecution,
    OperatorExecutionStatus,
)
from atlas.services.ai.operator.operator import AIModelOperator


class OperatorExecutionService:
    """
    Coordinates the lifecycle of one AI Operator execution.

    This service owns execution state transitions only.

    Model selection remains the responsibility of AIModelOperator.
    Actual LLM execution remains the responsibility of the caller/runtime.
    """

    def __init__(
        self,
        operator: AIModelOperator,
    ):
        self.operator = operator

    def create(
        self,
        request: AIRequest,
    ) -> OperatorExecution:

        return OperatorExecution(
            execution_id=str(uuid4()),
            task=request.task,
        )

    def select_model(
        self,
        execution: OperatorExecution,
        request: AIRequest,
        runtime,
    ):

        self._transition(
            execution,
            OperatorExecutionStatus.SELECTING_MODEL,
        )

        model = self.operator.select(
            request.task,
            runtime,
        )

        if not model:
            execution.status = (
                OperatorExecutionStatus.FAILED
            )

            execution.error = (
                "No suitable AI model is available"
            )

            execution.completed_at = (
                datetime.now(timezone.utc)
            )

            return None

        execution.model = model.name
        execution.provider = model.provider
        execution.provider_model = (
            model.provider_model
        )

        self._transition(
            execution,
            OperatorExecutionStatus.MODEL_SELECTED,
        )

        return model

    def execute(
        self,
        execution: OperatorExecution,
        request: AIRequest,
        executor: Callable[[AIRequest], LLMResponse],
    ) -> LLMResponse:

        if execution.status != (
            OperatorExecutionStatus.MODEL_SELECTED
        ):
            raise RuntimeError(
                "Execution must have a selected model "
                "before execution"
            )

        self._transition(
            execution,
            OperatorExecutionStatus.EXECUTING,
        )

        try:
            response = executor(request)

        except Exception as exc:
            execution.status = (
                OperatorExecutionStatus.FAILED
            )

            execution.error = str(exc)

            execution.completed_at = (
                datetime.now(timezone.utc)
            )

            raise

        if not response:
            execution.status = (
                OperatorExecutionStatus.FAILED
            )

            execution.error = (
                "LLM executor returned no response"
            )

            execution.completed_at = (
                datetime.now(timezone.utc)
            )

            raise RuntimeError(
                "LLM executor returned no response"
            )

        if response.metadata.get("error"):
            execution.status = (
                OperatorExecutionStatus.FAILED
            )

            execution.error = str(
                response.metadata["error"]
            )

            execution.completed_at = (
                datetime.now(timezone.utc)
            )

            return response

        execution.status = (
            OperatorExecutionStatus.COMPLETED
        )

        execution.completed_at = (
            datetime.now(timezone.utc)
        )

        return response

    @staticmethod
    def _transition(
        execution: OperatorExecution,
        status: OperatorExecutionStatus,
    ):

        execution.status = status
