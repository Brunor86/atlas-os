from atlas.services.ai.chat.context import ChatContextBuilder
from atlas.services.ai.chat.conversation import Conversation


def test_context_contains_system_prompt():
    conversation = Conversation()
    conversation.add_user_message("¿Cómo está ATLAS?")

    builder = ChatContextBuilder()

    messages = builder.build_messages(conversation)

    assert messages[0]["role"] == "system"
    assert "You are ATLAS" in messages[0]["content"]


def test_context_preserves_conversation_history():
    conversation = Conversation()

    conversation.add_user_message("¿Qué pasó con Jellyseerr?")
    conversation.add_assistant_message(
        "Voy a revisar la información disponible."
    )
    conversation.add_user_message(
        "¿Y ahora?"
    )

    builder = ChatContextBuilder()

    messages = builder.build_messages(conversation)

    assert messages[1:] == [
        {
            "role": "user",
            "content": "¿Qué pasó con Jellyseerr?",
        },
        {
            "role": "assistant",
            "content": "Voy a revisar la información disponible.",
        },
        {
            "role": "user",
            "content": "¿Y ahora?",
        },
    ]


def test_infrastructure_is_not_injected_into_context():
    conversation = Conversation()

    conversation.add_user_message(
        "¿Cuál es la temperatura del disco?"
    )

    builder = ChatContextBuilder()

    messages = builder.build_messages(conversation)

    serialized = str(messages)

    assert "WD Red Pro" not in serialized
    assert "/dev/sdb" not in serialized
