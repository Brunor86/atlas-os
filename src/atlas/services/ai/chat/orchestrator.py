from atlas.services.ai.models import AIRequest

from atlas.services.ai.chat.reference import (
    AssetReferenceResolver,
)

from atlas.services.intelligence.operator_tools.assets import (
    AssetTools,
)


class ChatOrchestrator:
    """
    Coordinates conversational requests.

    Pipeline:

        conversation
            ↓
        reference resolution
            ↓
        infrastructure context
            ↓
        AIService
    """

    def __init__(
        self,
        ai_service,
        context_builder,
        *,
        asset_tools=None,
    ):
        self.ai_service = ai_service
        self.context_builder = context_builder

        self.asset_tools = (
            asset_tools
            or AssetTools()
        )

        self.reference_resolver = (
            AssetReferenceResolver(
                self.asset_tools
            )
        )

    def ask(
        self,
        conversation,
        prompt: str,
        *,
        task: str = "summary",
        priority: str = "normal",
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ):

        conversation.add_user_message(
            prompt
        )

        reference = (
            self.reference_resolver.resolve(
                prompt,
                conversation,
            )
        )

        if reference:

            self.reference_resolver.remember(
                conversation,
                reference,
            )

        request_prompt = self._build_prompt(
            conversation,
            reference=reference,
        )

        request = AIRequest(
            task=task,
            user_prompt=request_prompt,
            priority=priority,
            context_required=True,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        response = self.ai_service.ask(
            request
        )

        conversation.add_assistant_message(
            response.content,
            metadata={
                "model": response.model,
                "provider": response.provider,
                "latency_ms": response.latency_ms,
                "tokens": response.tokens,
                "execution_id": (
                    response.metadata.get(
                        "execution_id"
                    )
                ),
            },
        )

        return response

    def _build_prompt(
        self,
        conversation,
        *,
        reference=None,
    ) -> str:

        messages = (
            self.context_builder.build_messages(
                conversation,
                reference=reference,
            )
        )

        return self._serialize_messages(
            messages
        )

    @staticmethod
    def _serialize_messages(
        messages: list[dict],
    ) -> str:

        parts = []

        for message in messages:

            role = message.get(
                "role",
                "user",
            )

            content = message.get(
                "content",
                "",
            )

            if not content:
                continue

            parts.append(
                f"{role.upper()}:\n{content}"
            )

        return "\n\n".join(parts)
