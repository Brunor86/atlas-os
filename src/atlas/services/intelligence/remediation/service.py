from datetime import datetime, UTC


class RemediationService:


    def evaluate(
        self,
        execution,
        incident=None,
    ):


        if not execution:


            return {

                "status": "UNKNOWN",

                "reason": [
                    "no execution result available"
                ],

                "confidence": 0,

                "generated_at":
                    datetime.now(UTC).isoformat(),

            }



        if execution.status == "SUCCESS":


            return {


                "status":
                    "RESOLVED",


                "confidence":
                    1.0,


                "reason": [

                    "automatic remediation succeeded",

                    execution.result,

                ],


                "evidence":
                    execution.evidence,


                "generated_at":
                    datetime.now(UTC).isoformat(),


            }



        return {


            "status":
                "FAILED",


            "confidence":
                0,


            "reason": [

                "automatic remediation failed",

            ],


            "evidence":
                getattr(
                    execution,
                    "evidence",
                    []
                ),


            "generated_at":
                datetime.now(UTC).isoformat(),


        }
