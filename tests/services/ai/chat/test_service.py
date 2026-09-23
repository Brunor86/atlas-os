import pytest

from atlas.services.ai.chat.service import ChatService


class FakeResponse:

    content = "Respuesta ATLAS"

    model = "qwen3.5:9b"

    provider = "ollama"

    latency_ms = 10

    tokens = 20

    metadata = {
        "execution_id": "exec-1",
    }


class FakeAIService:

    def ask(self, request):
        return FakeResponse()


def test_create_conversation():
    service = ChatService(
        ai_service=FakeAIService()
    )

    conversation = service.create_conversation()

    assert conversation.conversation_id
    assert (
        service.get_conversation(
            conversation.conversation_id
        )
        is conversation
    )


def test_ask_creates_conversation():
    service = ChatService(
        ai_service=FakeAIService()
    )

    result = service.ask(
        "Hola ATLAS"
    )

    assert result["conversation_id"]
    assert result["response"].content == (
        "Respuesta ATLAS"
    )

    conversation = result["conversation"]

    assert len(conversation.messages) == 2


def test_ask_reuses_conversation():
    service = ChatService(
        ai_service=FakeAIService()
    )

    first = service.ask(
        "¿Cómo estás?"
    )

    conversation_id = first["conversation_id"]

    second = service.ask(
        "¿Y ahora?",
        conversation_id=conversation_id,
    )

    assert (
        second["conversation_id"]
        == conversation_id
    )

    conversation = second["conversation"]

    assert len(conversation.messages) == 4


def test_unknown_conversation_fails():
    service = ChatService(
        ai_service=FakeAIService()
    )

    with pytest.raises(ValueError):
        service.ask(
            "Hola",
            conversation_id="does-not-exist",
        )


def test_clear_conversation():
    service = ChatService(
        ai_service=FakeAIService()
    )

    result = service.ask("Hola")

    conversation_id = result["conversation_id"]

    assert service.clear(conversation_id)

    conversation = service.get_conversation(
        conversation_id
    )

    assert conversation.messages == []


def test_clear_unknown_conversation():
    service = ChatService(
        ai_service=FakeAIService()
    )

    assert (
        service.clear("does-not-exist")
        is False
    )
