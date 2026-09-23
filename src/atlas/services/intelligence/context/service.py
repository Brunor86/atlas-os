from atlas.models.intelligence import IntelligenceContext


class IntelligenceContextService:


    def __init__(
        self,
        repository=None,
    ):

        self.repository = repository



    def build(
        self,
        snapshot=None,
        events=None,
        incidents=None,
        history=None,
        assets=None,
        actions=None,
    ):


        context = IntelligenceContext()


        context.environment = snapshot or {}

        context.events = events or []

        context.incidents = incidents or []

        context.history = history or []

        context.assets = assets or []

        context.actions = actions or []


        return context
