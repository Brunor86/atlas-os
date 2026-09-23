import json
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ReasoningGateResult:

    escalate: bool

    score: float

    reasons: list[str]


class AIReasoningGate:

    MIN_CONFIDENCE = 0.70
    MIN_SCORE = 0.70

    def evaluate(
        self,
        content: str,
        *,
        task: str,
    ) -> ReasoningGateResult:

        reasons = []

        score = 1.0

        parsed: dict[str, Any] | None = None

        #
        # Try to interpret the model response as
        # structured reasoning.
        #

        try:

            value = json.loads(
                content
            )

            if isinstance(
                value,
                dict,
            ):
                parsed = value

        except (
            TypeError,
            ValueError,
        ):

            parsed = None

        #
        # Reasoning tasks require stronger validation.
        #

        if task in {
            "incident_reasoning",
            "diagnosis",
            "root_cause",
            "reasoning",
        }:

            #
            # Structured response.
            #

            if parsed is not None:

                confidence = parsed.get(
                    "confidence"
                )

                #
                # Confidence is mandatory for
                # structured reasoning.
                #

                if isinstance(
                    confidence,
                    (int, float),
                ):

                    if confidence < self.MIN_CONFIDENCE:

                        score -= 0.30

                        reasons.append(
                            "low model confidence"
                        )

                else:

                    score -= 0.15

                    reasons.append(
                        "missing confidence"
                    )

                #
                # Missing evidence means the model
                # explicitly knows that the diagnosis
                # is incomplete.
                #

                missing = parsed.get(
                    "missing_evidence",
                    [],
                )

                if missing:

                    score -= 0.20

                    reasons.append(
                        "missing evidence reported"
                    )

                #
                # Root cause is important for deep
                # incident reasoning.
                #

                root_cause = parsed.get(
                    "root_cause"
                )

                if not root_cause:

                    score -= 0.20

                    reasons.append(
                        "root cause not established"
                    )

                #
                # Evidence must exist.
                #

                evidence = parsed.get(
                    "evidence",
                    [],
                )

                if not evidence:

                    score -= 0.15

                    reasons.append(
                        "insufficient evidence"
                    )

            #
            # Free-form reasoning is allowed, but
            # receives a lower confidence because ATLAS
            # cannot validate its structure.
            #

            else:

                score -= 0.20

                reasons.append(
                    "unstructured reasoning response"
                )

        #
        # Clamp score.
        #

        score = max(
            0.0,
            min(
                1.0,
                score,
            ),
        )

        return ReasoningGateResult(

            escalate=(
                score < self.MIN_SCORE
            ),

            score=score,

            reasons=reasons,

        )
