
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class ModelRuntimeState:

    model: str

    provider_model: str | None = None

    installed: bool = False

    loaded: bool = False

    loaded_at: datetime | None = None

    requests: int = 0

    successes: int = 0

    failures: int = 0

    last_error: str | None = None

    last_latency_ms: float = 0



    def health(self):

        if not self.installed:

            return "DEGRADED"

        if self.failures > self.successes:

            return "DEGRADED"

        if self.requests == 0:

            return "UNKNOWN"

        return "HEALTHY"




class AIModelRuntime:


    def __init__(self):

        self.models = {}



    def register(
        self,
        model: str,
        provider_model: str | None = None,
    ):

        self.models[model] = ModelRuntimeState(

            model=model,

            provider_model=provider_model,

        )



    def mark_installed(
        self,
        model: str,
        installed: bool = True,
    ):

        state = self.models.get(
            model
        )

        if state:

            state.installed = installed




    def load(
        self,
        model: str,
    ):

        state = self.models.get(
            model
        )

        if state:

            state.loaded = True

            state.loaded_at = datetime.now(timezone.utc)



    def unload(
        self,
        model: str,
    ):

        state = self.models.get(
            model
        )

        if state:

            state.loaded = False



    def unload_all(self):

        for state in self.models.values():

            state.loaded = False




    def record_request(
        self,
        model: str,
    ):

        state = self.models.get(
            model
        )

        if state:

            state.requests += 1




    def record_success(
        self,
        model: str,
        latency_ms: float = 0,
    ):

        state = self.models.get(
            model
        )

        if state:

            state.successes += 1

            state.last_latency_ms = latency_ms

            state.last_error = None




    def record_failure(
        self,
        model: str,
        error: str,
        latency_ms: float = 0,
    ):

        state = self.models.get(
            model
        )

        if state:

            state.failures += 1

            state.last_error = error

            state.last_latency_ms = latency_ms




    def status(self):

        return list(
            self.models.values()
        )
