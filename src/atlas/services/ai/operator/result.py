from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OperatorResult(BaseModel):
    """
    Final result contract returned by an AI Operator execution.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    execution_id: str = Field(
        min_length=1,
    )

    success: bool

    data: Any = None

    evidence: list[Any] = Field(
        default_factory=list,
    )

    error: str | None = None

    metadata: dict[str, object] = Field(
        default_factory=dict,
    )
