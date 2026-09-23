from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OperatorToolResult(BaseModel):
    """
    Contract returned by every AI Operator tool.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    tool: str = Field(
        min_length=1,
    )

    success: bool

    data: Any = None

    error: str | None = None

    evidence: list[Any] = Field(
        default_factory=list,
    )


class OperatorTool(ABC):

    name: str = ""

    description: str = ""

    @abstractmethod
    def execute(
        self,
        **kwargs,
    ) -> OperatorToolResult:
        raise NotImplementedError
