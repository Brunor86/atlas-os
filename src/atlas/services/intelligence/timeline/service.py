from atlas.models.reasoning import ReasoningStep


class TimelineIntelligenceService:


    def __init__(self):

        self.steps = []


    def add_step(
        self,
        stage,
        title,
        data=None,
        confidence=0.0,
    ):

        step = ReasoningStep(

            stage=stage,

            title=title,

            data=data or {},

            confidence=confidence,

        )


        self.steps.append(
            step
        )


        return step


    def add_event(
        self,
        stage,
        title,
        data=None,
    ):

        return self.add_step(

            stage=stage,

            title=title,

            data=data,

        )


    def build(
        self,
    ):

        return {

            "timeline": [

                step.to_dict()

                for step in self.steps

            ],

            "count": len(
                self.steps
            ),

        }


    def clear(
        self,
    ):

        self.steps = []
