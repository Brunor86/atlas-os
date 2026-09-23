class IntelligenceHistoryService:


    def __init__(
        self,
        repository=None,
    ):

        self.repository = repository



    def get_asset_history(
        self,
        asset_id,
    ):

        if not self.repository:
            return []


        return self.repository.get_asset_incidents(
            asset_id
        )



    def get_root_cause_frequency(
        self,
    ):

        if not self.repository:
            return {}


        return self.repository.get_root_cause_frequency()



    def get_severity_trend(
        self,
    ):

        if not self.repository:
            return []


        return self.repository.get_severity_trend()


    def get_similar_incidents(
        self,
        asset_id,
        root_cause,
    ):

        if not self.repository:
            return []


        return self.repository.get_similar_incidents(
            asset_id,
            root_cause,
        )
