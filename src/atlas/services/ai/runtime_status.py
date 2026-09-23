from atlas.services.ai.service import AIService


class AIRuntimeStatusService:

    def __init__(self):
        self.ai = AIService()

    def status(self):

        runtime = self.ai.runtime

        runtime_health = self.ai.health.status()

        installed = [
            {
                "model": item.model,
                "provider_model": item.provider_model,
                "installed": item.installed,
            }
            for item in runtime.status()
        ]

        installed_count = sum(1 for m in installed if m["installed"])
        pending_count = sum(1 for m in installed if not m["installed"])

        return {
            "status": runtime_health.get(
                "status",
                "UNKNOWN",
            ),
            "runtime": self.ai.runtime_target.provider,
            "target": {
                "host": self.ai.runtime_target.host,
                "port": self.ai.runtime_target.port,
            },
            "installed_models": installed_count,
            "pending_models": pending_count,
            "models": installed,
        }
