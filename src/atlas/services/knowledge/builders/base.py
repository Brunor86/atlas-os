from abc import ABC
from abc import abstractmethod


class KnowledgeBuilder(ABC):

    @abstractmethod
    def build(
        self,
        asset,
        card,
        graph,
    ):
        pass
