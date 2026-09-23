from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """
    Base interface for any Large Language Model backend.

    Implementations:
        - Ollama
        - OpenAI
        - LM Studio
        - llama.cpp
        - etc.
    """

    @abstractmethod
    def available(self) -> bool:
        """Returns True if the provider is ready."""
        raise NotImplementedError

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
    ) -> str:
        """Generate a response from the model."""
        raise NotImplementedError
