from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: dict = field(default_factory=dict)


@dataclass
class Conversation:
    conversation_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    messages: list[ChatMessage] = field(
        default_factory=list
    )

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    metadata: dict = field(
        default_factory=dict
    )

    def add_user_message(
        self,
        content: str,
    ) -> ChatMessage:

        return self._add_message(
            role="user",
            content=content,
        )

    def add_assistant_message(
        self,
        content: str,
        *,
        metadata: dict | None = None,
    ) -> ChatMessage:

        return self._add_message(
            role="assistant",
            content=content,
            metadata=metadata or {},
        )

    def _add_message(
        self,
        *,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> ChatMessage:

        message = ChatMessage(
            role=role,
            content=content,
            metadata=metadata or {},
        )

        self.messages.append(message)

        self.updated_at = datetime.now(
            timezone.utc
        )

        return message

    def history(
        self,
    ) -> list[dict]:

        return [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in self.messages
        ]

    def last_message(
        self,
    ) -> ChatMessage | None:

        if not self.messages:
            return None

        return self.messages[-1]

    def clear(self):

        self.messages.clear()

        self.updated_at = datetime.now(
            timezone.utc
        )
