from abc import ABC, abstractmethod


class Collector(ABC):
    """
    Clase base para todos los collectors de ATLAS.
    """

    name: str = "unknown"

    @abstractmethod
    def collect(self):
        """
        Ejecuta descubrimiento y devuelve información de infraestructura.
        """
        pass
