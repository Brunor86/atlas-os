from abc import ABC
from logging import Logger

from atlas.utils.logger import get_logger


class BaseService(ABC):
    """Clase base para todos los servicios de ATLAS."""

    def __init__(self) -> None:
        self.logger: Logger = get_logger(self.__class__.__name__)
