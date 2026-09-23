from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class AIRecommendation(BaseModel):
    """
    Structured recommendation produced by the AI layer.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    title: str = Field(
        min_length=1,
    )

    description: str = Field(
        min_length=1,
    )

    priority: str = Field(
        min_length=1,
    )

    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
    )


class AIReasoningStep(BaseModel):
    """
    Structured reasoning step produced by the AI layer.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    step: str = Field(
        min_length=1,
    )

    evidence: str = Field(
        min_length=1,
    )

    impact: str = Field(
        min_length=1,
    )

    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
    )


class AIResponse(BaseModel):
    """
    Structured AI analysis response.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    timestamp: datetime

    summary: str

    overall_risk: int

    overall_health: float

    context: dict[str, Any] = Field(
        default_factory=dict,
    )

    incidents: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    impacts: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    recommendations: list[AIRecommendation] = Field(
        default_factory=list,
    )

    reasoning: list[str] = Field(
        default_factory=list,
    )

    reasoning_steps: list[AIReasoningStep] = Field(
        default_factory=list,
    )


class AIRequest(BaseModel):
    """
    Validated input contract for the AI service.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    task: str = Field(
        min_length=1,
    )

    user_prompt: str = Field(
        min_length=1,
    )

    priority: str = Field(
        default="normal",
        min_length=1,
    )

    context_required: bool = True

    max_tokens: int = Field(
        default=2048,
        gt=0,
    )

    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
    )


class LLMResponse(BaseModel):
    """
    Validated output contract returned by an LLM provider.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    model: str = Field(
        min_length=1,
    )

    provider: str = Field(
        min_length=1,
    )

    content: str

    latency_ms: float = Field(
        default=0,
        ge=0,
    )

    tokens: int = Field(
        default=0,
        ge=0,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
