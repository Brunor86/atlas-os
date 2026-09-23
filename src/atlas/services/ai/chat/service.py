from atlas.services.ai.chat.context import ChatContextBuilder
from atlas.services.ai.chat.conversation import Conversation
from atlas.services.ai.chat.orchestrator import ChatOrchestrator


class ChatService:
    """
    Public conversational interface for ATLAS.

    Owns conversations and delegates execution to the existing
    AIService/operator pipeline.
    """

    def __init__(
        self,
        ai_service=None,
    ):
        if ai_service is None:
            from atlas.services.ai.service import AIService

            ai_service = AIService()

        self.ai_service = ai_service

        self.context_builder = (
            ChatContextBuilder()
        )

        self.orchestrator = (
            ChatOrchestrator(
                ai_service=self.ai_service,
                context_builder=self.context_builder,
            )
        )

        self.conversations = {}

    def create_conversation(
        self,
    ) -> Conversation:

        conversation = Conversation()

        self.conversations[
            conversation.conversation_id
        ] = conversation

        return conversation

    def get_conversation(
        self,
        conversation_id: str,
    ) -> Conversation | None:

        return self.conversations.get(
            conversation_id
        )

    def ask(
        self,
        prompt: str,
        *,
        conversation_id: str | None = None,
        task: str = "summary",
        priority: str = "normal",
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ):

        if conversation_id:

            conversation = (
                self.get_conversation(
                    conversation_id
                )
            )

            if conversation is None:

                raise ValueError(
                    f"Unknown conversation: "
                    f"{conversation_id}"
                )

        else:

            conversation = (
                self.create_conversation()
            )

        response = self.orchestrator.ask(
            conversation,
            prompt,
            task=task,
            priority=priority,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return {
            "conversation_id":
                conversation.conversation_id,

            "response":
                response,

            "conversation":
                conversation,
        }

    def clear(
        self,
        conversation_id: str,
    ):

        conversation = (
            self.get_conversation(
                conversation_id
            )
        )

        if conversation is None:
            return False

        conversation.clear()

        return True
