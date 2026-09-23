from atlas.services.events.correlation import EventCorrelation


class NOCCorrelation:


    def __init__(self):

        self.engine = EventCorrelation()



    def analyze(self, events):

        if not events:
            return []


        return self.engine.analyze(
            events
        )
