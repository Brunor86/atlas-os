
from dataclasses import dataclass


@dataclass(slots=True)
class AIRuntimeTarget:

    name: str

    provider: str

    host: str

    port: int

    enabled: bool = True


    @property
    def url(self):

        return f"{self.provider}://{self.host}:{self.port}"
