from __future__ import annotations

from abc import ABC, abstractmethod

from atlas.core.asset import Asset


class AssetProvider(ABC):
    """
    Clase base para cualquier proveedor de Assets.
    """

    @abstractmethod
    def collect(self) -> list[Asset]:
        """
        Descubre Assets y los devuelve.
        """
        raise NotImplementedError
