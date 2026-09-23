class ChatContextBuilder:
    """
    Builds conversational context for ATLAS Chat.
    """

    SYSTEM_PROMPT = """
You are ATLAS, an intelligent infrastructure operator.

You are connected to a real infrastructure environment.

Your knowledge comes from:
- conversation history
- resolved infrastructure assets
- ATLAS infrastructure data
- operator tools
- graph relationships
- evidence

Rules:

1. Never invent infrastructure facts.
2. Infrastructure facts must come from ATLAS evidence.
3. Conversation references such as "ese servidor",
   "ese contenedor" or "el anterior" may already have
   been resolved by ATLAS.
4. Never override a resolved asset with a guess.
5. Distinguish clearly between observed facts and inference.
6. Answer naturally in Spanish when the user speaks Spanish.
7. Be concise for simple questions.
8. Explain relationships when they matter.
9. Do not claim an action was executed unless ATLAS actually
   executed it.
""".strip()

    def system_prompt(self) -> str:
        return self.SYSTEM_PROMPT

    def build_messages(
        self,
        conversation,
        *,
        reference=None,
    ) -> list[dict]:

        messages = [
            {
                "role": "system",
                "content": self.system_prompt(),
            }
        ]

        if reference:

            messages.append(
                {
                    "role": "system",
                    "content": (
                        "RESOLVED ASSET\n"
                        f"id={reference.asset_id}\n"
                        f"name={reference.asset_name}\n"
                        f"confidence={reference.confidence}\n"
                        f"source={reference.source}"
                    ),
                }
            )

        messages.extend(
            conversation.history()
        )

        return messages
