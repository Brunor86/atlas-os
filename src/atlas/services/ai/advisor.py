from datetime import datetime, UTC

from atlas.services.ai.context import AIContextBuilder
from atlas.services.ai.models import (
    AIRecommendation,
    AIResponse,
    AIRequest,
    AIReasoningStep,
)

from atlas.services.ai.service import AIService
from atlas.services.ai.severity import AISeverityEngine


class AIAdvisor:

    """
    Main intelligence entry point.
    """

    def __init__(self):

        self.context_builder = AIContextBuilder()

        self.ai_service = AIService()

        self.severity = AISeverityEngine()


    def advise(self):

        context = self.context_builder.build()

        findings = context.get(
            "health",
            {},
        ).get(
            "findings",
            [],
        )


        from atlas.core.finding import HealthFinding


        findings = [

            HealthFinding(

                asset_id=f.get("asset_id"),

                severity=f.get("severity"),

                title=f.get("title"),

                message=f.get("message"),

                category=f.get("category"),

                occurrences=f.get(
                    "occurrences",
                    1,
                ),

            )

            if isinstance(f, dict)

            else f

            for f in findings

        ]

        recommendations = []

        reasoning = []

        reasoning_steps = []

        risk = 0

        health = 100

        summary = "Infrastructure healthy."


        if findings:

            severity_result = self.severity.score(
                findings
            )

            risk = severity_result["risk"]

            health -= min(
                risk // 2,
                100,
            )

            summary = (
                f"{len(findings)} active health findings detected."
                f" Risk score: {risk}/100."
            )

            reasoning.append(
                summary
            )

            reasoning_steps.append(
                AIReasoningStep(
                    step="severity_analysis",
                    evidence=f"{len(findings)} health findings analyzed",
                    impact=f"Calculated infrastructure risk score: {risk}/100",
                    confidence=0.95,
                )
            )

            recommendations.append(

                AIRecommendation(

                    title="Review health findings",

                    description=(
                        "Investigate active health alerts before they escalate."
                    ),

                    priority="HIGH",

                    confidence=0.95,

                )

            )


        #
        # Optional AI explanation
        #

        try:

            llm_response = self.ai_service.ask(

                AIRequest(

                    task="summary",

                    user_prompt=(

                        "Summarize the current infrastructure status.\n\n"

                        f"{summary}\n"

                        f"Risk score: {risk}\n"

                        f"Health score: {health}\n"

                    ),

                )

            )


            if llm_response.content not in [

                "LLM unavailable",

                "No model available",

                "Provider unavailable",

            ]:

                reasoning.append(

                    llm_response.content

                )


        except Exception as exc:

            reasoning.append(

                f"AI service unavailable: {exc}"

            )


        return AIResponse(

            timestamp=datetime.now(UTC),

            summary=summary,

            overall_risk=risk,

            overall_health=max(
                health,
                0,
            ),

            context=context,

            recommendations=recommendations,

            reasoning=reasoning,

            reasoning_steps=reasoning_steps,

        )
