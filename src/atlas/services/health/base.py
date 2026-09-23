from abc import ABC, abstractmethod

from atlas.models.health import HealthInfo


class HealthRule(ABC):

    @abstractmethod
    def evaluate(self, infra, health: HealthInfo) -> None:
        """Evalua una regla de salud sobre la infraestructura."""
        pass
