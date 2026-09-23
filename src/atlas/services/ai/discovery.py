from atlas.services.ai.runtime import AIModelRuntime
from atlas.services.ai.operator.operator import AIModelOperator


class AIModelDiscovery:

    def __init__(
        self,
        operator: AIModelOperator,
        runtime: AIModelRuntime,
        providers: dict,
    ):

        self.operator = operator

        self.runtime = runtime

        self.providers = providers

    def scan(self):

        results = []

        installed_models = set()

        ollama = self.providers.get(
            "ollama"
        )

        if ollama:

            try:

                installed_models = set(
                    ollama.models()
                )

            except Exception:

                installed_models = set()

        for model in self.operator.list_models():

            provider_model = model.provider_model

            installed = (
                provider_model
                in installed_models
            )

            self.runtime.mark_installed(
                model.name,
                installed,
            )

            results.append(

                {
                    "model":
                        model.name,

                    "provider":
                        model.provider,

                    "provider_model":
                        provider_model,

                    "installed":
                        installed,

                    "capabilities": {

                        "reasoning":
                            model.capabilities.reasoning,

                        "summary":
                            model.capabilities.summary,

                        "coding":
                            model.capabilities.coding,

                    },

                }

            )

        return results
