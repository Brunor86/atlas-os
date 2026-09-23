from datetime import timezone

from atlas.services.ai.chat.conversation import (
    ChatMessage,
    Conversation,
)


def test_conversation_starts_empty():
    conversation = Conversation()

    assert conversation.messages == []
    assert conversation.last_message() is None


def test_add_user_message():
    conversation = Conversation()

    message = conversation.add_user_message(
        "¿Cómo está el servidor?"
    )

    assert isinstance(message, ChatMessage)
    assert message.role == "user"
    assert message.content == "¿Cómo está el servidor?"
    assert conversation.last_message() == message
    assert message.timestamp.tzinfo == timezone.utc


def test_add_assistant_message_with_metadata():
    conversation = Conversation()

    message = conversation.add_assistant_message(
        "El servidor está operativo.",
        metadata={
            "model": "qwen3.5:9b",
            "execution_id": "exec-123",
        },
    )

    assert message.role == "assistant"
    assert message.metadata["model"] == "qwen3.5:9b"
    assert message.metadata["execution_id"] == "exec-123"


def test_history_returns_llm_messages():
    conversation = Conversation()

    conversation.add_user_message("Hola")
    conversation.add_assistant_message("Hola, soy ATLAS")

    assert conversation.history() == [
        {
            "role": "user",
            "content": "Hola",
        },
        {
            "role": "assistant",
            "content": "Hola, soy ATLAS",
        },
    ]


def test_clear_removes_history():
    conversation = Conversation()

    conversation.add_user_message("Hola")
    conversation.add_assistant_message("Hola")

    assert conversation.clear() is None
    assert conversation.messages == []
    assert conversation.last_message() is None
