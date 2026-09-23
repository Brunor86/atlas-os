from abc import ABC, abstractmethod

from atlas.core.asset import Asset


class DiscoveryProvider(ABC):
    """
    Base class for infrastructure discovery providers.
    """

    name: str = "unknown"

    @abstractmethod
    def discover(self) -> list[Asset]:
        """
        Discover assets from a source.
        """
        raise NotImplementedError
