from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)


class OperationPlan(BaseModel):
    """
    Typed operational intent produced by the AI planning boundary.

    This object is NOT an executable action.

    PROPOSE means:
        the user's request may be materialized as an ATLAS
        SafeAction proposal.

    NONE means:
        no operational proposal is authorized from this request.
    """

    intent: Literal[
        "NONE",
        "PROPOSE",
    ] = "NONE"

    resource_type: Literal[
        "container",
        "service",
        "vm",
        "lxc",
    ] | None = None

    action: Literal[
        "start",
        "restart",
        "stop",
    ] | None = None

    target: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=(
            r"^[A-Za-z0-9]"
            r"[A-Za-z0-9_.-]{0,127}$"
        ),
    )

    reason: str = Field(
        min_length=1,
        max_length=500,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )


    @model_validator(
        mode="after"
    )
    def validate_intent(
        self,
    ):

        if (
            self.intent
            == "PROPOSE"
        ):

            if (
                self.resource_type is None
                or self.action is None
                or self.target is None
            ):
                raise ValueError(
                    "PROPOSE requires resource_type, action and target"
                )

            return self


        if (
            self.resource_type is not None
            or self.action is not None
            or self.target is not None
        ):
            raise ValueError(
                "NONE must not contain resource_type, action or target"
            )

        return self
