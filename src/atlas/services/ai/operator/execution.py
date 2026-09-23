from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class OperatorExecutionStatus(StrEnum):
    CREATED = "created"
    SELECTING_MODEL = "selecting_model"
    MODEL_SELECTED = "model_selected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class OperatorExecution(BaseModel):
    """
    Contract describing one AI Operator execution.

    This model represents execution state only.
    It does not contain reasoning or action intelligence.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    execution_id: str = Field(
        min_length=1,
    )

    task: str = Field(
        min_length=1,
    )

    status: OperatorExecutionStatus = (
        OperatorExecutionStatus.CREATED
    )

    model: str | None = None

    provider: str | None = None

    provider_model: str | None = None

    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    completed_at: datetime | None = None

    error: str | None = None
