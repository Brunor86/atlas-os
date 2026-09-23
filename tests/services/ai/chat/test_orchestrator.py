from types import SimpleNamespace

from atlas.services.ai.chat.context import ChatContextBuilder
from atlas.services.ai.chat.conversation import Conversation
from atlas.services.ai.chat.orchestrator import ChatOrchestrator


class FakeAIService:

    def __init__(self):
        self.requests = []

    def ask(self, request):
        self.requests.append(request)

        return SimpleNamespace(
            content="Respuesta de prueba de ATLAS.",
            model="qwen3.5:9b",
            provider="ollama",
            latency_ms=12,
            tokens=42,
            metadata={
                "execution_id": "exec-test",
            },
        )


def test_orchestrator_sends_conversation_to_ai():
    ai = FakeAIService()

    orchestrator = ChatOrchestrator(
        ai_service=ai,
        context_builder=ChatContextBuilder(),
    )

    conversation = Conversation()

    response = orchestrator.ask(
        conversation,
        "¿Cómo está el servidor?",
    )

    assert response.content == (
        "Respuesta de prueba de ATLAS."
    )

    assert len(ai.requests) == 1

    request = ai.requests[0]

    assert "You are ATLAS" in request.user_prompt
    assert "¿Cómo está el servidor?" in request.user_prompt
    assert request.task == "summary"


def test_orchestrator_persists_assistant_response():
    ai = FakeAIService()

    orchestrator = ChatOrchestrator(
        ai_service=ai,
        context_builder=ChatContextBuilder(),
    )

    conversation = Conversation()

    orchestrator.ask(
        conversation,
        "Hola ATLAS",
    )

    assert len(conversation.messages) == 2

    assert conversation.messages[0].role == "user"
    assert conversation.messages[1].role == "assistant"

    assert (
        conversation.messages[1].content
        == "Respuesta de prueba de ATLAS."
    )

    assert (
        conversation.messages[1]
        .metadata["execution_id"]
        == "exec-test"
    )


def test_conversation_history_is_sent_on_followup():
    ai = FakeAIService()

    orchestrator = ChatOrchestrator(
        ai_service=ai,
        context_builder=ChatContextBuilder(),
    )

    conversation = Conversation()

    orchestrator.ask(
        conversation,
        "¿Qué servidor está fallando?",
    )

    orchestrator.ask(
        conversation,
        "¿Y su temperatura?",
    )

    request = ai.requests[-1]

    assert "¿Qué servidor está fallando?" in request.user_prompt
    assert "¿Y su temperatura?" in request.user_prompt
