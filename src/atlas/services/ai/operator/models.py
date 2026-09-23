from pydantic import BaseModel, ConfigDict, Field, model_validator


class AIModelCapabilities(BaseModel):
    """
    Declarative capabilities exposed by an AI model.

    This is an Operator contract: it describes what a model
    can do, not how the model is executed.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    coding: bool = False
    reasoning: bool = False
    summary: bool = False

    context_window: int = Field(
        default=4096,
        ge=1,
    )

    parameter_size: str | None = None


class AIModelProfile(BaseModel):
    """
    Contract describing an AI model known by the Operator.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    name: str = Field(
        min_length=1,
    )

    provider: str = Field(
        min_length=1,
    )

    provider_model: str = Field(
        min_length=1,
    )

    capabilities: AIModelCapabilities

    priority: int = Field(
        default=100,
        ge=0,
    )

    fallback_for: str | None = None

    @model_validator(mode="after")
    def validate_fallback(self):
        if self.fallback_for == self.name:
            raise ValueError(
                "A model cannot be its own fallback"
            )

        return self
