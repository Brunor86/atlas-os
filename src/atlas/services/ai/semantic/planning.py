from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


AssetTypeSelector = Literal[
    "VM",
    "LXC",
    "APPLICATION",
    "CONTAINER",
    "DATABASE",
    "STORAGE",
    "SERVER",
    "SERVICE",
    "NETWORK",
    "SENSOR",
]


StatusSelector = Literal[
    "ONLINE",
    "OFFLINE",
    "DEGRADED",
]


class InventoryQueryPlan(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    intent: Literal[
        "NONE",
        "INVENTORY",
    ]

    asset_types: list[
        AssetTypeSelector
    ] = Field(
        default_factory=list,
        max_length=10,
    )

    statuses: list[
        StatusSelector
    ] = Field(
        default_factory=list,
        max_length=3,
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
    def validate_plan(
        self,
    ):

        if (
            len(
                set(
                    self.asset_types
                )
            )
            != len(
                self.asset_types
            )
        ):

            raise ValueError(
                "asset_types must not contain duplicates"
            )

        if (
            len(
                set(
                    self.statuses
                )
            )
            != len(
                self.statuses
            )
        ):

            raise ValueError(
                "statuses must not contain duplicates"
            )

        if (
            self.intent
            == "NONE"
            and (
                self.asset_types
                or self.statuses
            )
        ):

            raise ValueError(
                "NONE must not contain inventory selectors"
            )

        return self
