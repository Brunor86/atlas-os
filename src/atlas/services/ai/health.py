from __future__ import annotations

from typing import Any


class AIRuntimeHealth:

    def __init__(
        self,
        runtime,
        target=None,
    ):
        self.runtime = runtime
        self.target = target

    def _provider_available(self) -> bool:
        """
        Check actual runtime/provider availability.

        Runtime model state alone is not sufficient because a model
        can be installed while the provider itself is unreachable.
        """
        if not self.target:
            return False

        try:
            from atlas.services.ai.llm.ollama import OllamaProvider

            if self.target.provider == "ollama":
                provider = OllamaProvider(
                    host=self.target.url.replace(
                        "ollama://",
                        "http://",
                        1,
                    ),
                )

                return provider.available()

        except Exception:
            return False

        return False

    def report(self) -> dict[str, Any]:

        states = self.runtime.status()

        total = len(states)

        installed = sum(
            1
            for state in states
            if state.installed
        )

        loaded = sum(
            1
            for state in states
            if state.loaded
        )

        requests = sum(
            state.requests
            for state in states
        )

        failures = sum(
            state.failures
            for state in states
        )

        missing_models = [
            state.provider_model or state.model
            for state in states
            if not state.installed
        ]

        provider_available = self._provider_available()

        if not provider_available:

            status = "OFFLINE"

            reason = (
                "AI runtime provider is unreachable"
            )

            recommendation = (
                "Verify Ollama availability and runtime connectivity"
            )

        elif failures > 0:

            status = "DEGRADED"

            reason = (
                "Runtime failures detected"
            )

            recommendation = (
                "Review local AI runtime failures"
            )

        elif installed == 0:

            status = "DEGRADED"

            reason = (
                "No local AI models installed"
            )

            recommendation = (
                "Install required Ollama models"
            )

        else:

            status = "HEALTHY"

            reason = (
                "Local AI runtime operational"
            )

            recommendation = (
                "Local AI runtime ready"
            )

        runtime_target = None

        if self.target:

            runtime_target = {
                "name": self.target.name,
                "provider": self.target.provider,
                "host": self.target.host,
                "port": self.target.port,
                "enabled": self.target.enabled,
            }

        return {
            "runtime_target": runtime_target,

            "status": status,

            "provider_available": provider_available,

            "reason": reason,

            "models": total,

            "installed": installed,

            "loaded": loaded,

            "requests": requests,

            "failures": failures,

            "missing_models": missing_models,

            "recommendation": recommendation,
        }

    def status(self) -> dict[str, Any]:
        """
        Public status contract used by AIRuntimeStatusService.
        """
        return self.report()
