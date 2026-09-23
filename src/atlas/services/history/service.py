from atlas.core.history import AssetHistory
from atlas.storage.history_repository import HistoryRepository


class HistoryService:

    def __init__(self):

        self.repository = HistoryRepository()


    def persist(
        self,
        asset,
    ):

        history = AssetHistory(

            asset_id=asset.id,

            health=asset.health,

            status=asset.status.name,

        )

        self.repository.save(
            history
        )
