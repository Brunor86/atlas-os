from atlas.models.learning import LearningRecord

from atlas.services.intelligence.learning.context import (
    LearningContextService
)



class IncidentLearningService:


    def __init__(
        self,
        repository=None,
    ):

        self.repository = repository

        self.context = LearningContextService(
            repository
        )



    def learn(
        self,
        incident_id,
        action,
        result,
        resolution="",
        evidence=None,
    ):

        confidence = 0


        if result in (
            "SUCCESS",
            "VERIFIED",
        ):

            confidence = 1.0


        elif result == "PARTIAL":

            confidence = 0.5



        record = LearningRecord(

            incident_id=incident_id,

            action=action,

            result=result,

            resolution=resolution,

            confidence=confidence,

            evidence=evidence or [],

        )


        if self.repository:

            self.repository.save_learning(
                record
            )


        return record




    def get_context(
        self,
        incident,
    ):

        return self.context.get_context(
            incident
        )

