import os
from dataclasses import dataclass


DEFAULT_OLLAMA_HOST = "127.0.0.1"
DEFAULT_OLLAMA_PORT = 11434


@dataclass(frozen=True)
class OllamaConfig:

    host: str

    port: int


def get_ollama_config() -> OllamaConfig:
    """
    Resolve the local/remote Ollama runtime endpoint.

    A public ATLAS installation must never contain a
    machine-specific infrastructure address in source code.

    By default Ollama is assumed to run locally. Remote AI
    runtimes can be selected explicitly through environment
    configuration.
    """

    host = (
        os.getenv(
            "ATLAS_OLLAMA_HOST"
        )
        or DEFAULT_OLLAMA_HOST
    ).strip()

    if not host:
        host = DEFAULT_OLLAMA_HOST

    raw_port = (
        os.getenv(
            "ATLAS_OLLAMA_PORT"
        )
        or str(
            DEFAULT_OLLAMA_PORT
        )
    ).strip()

    try:
        port = int(
            raw_port
        )

    except ValueError as exc:
        raise RuntimeError(
            "ATLAS_OLLAMA_PORT must be an integer"
        ) from exc

    if not (
        1
        <= port
        <= 65535
    ):
        raise RuntimeError(
            "ATLAS_OLLAMA_PORT must be between "
            "1 and 65535"
        )

    return OllamaConfig(
        host=host,
        port=port,
    )
