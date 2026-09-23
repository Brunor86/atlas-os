class ActionApprovalPolicy:


    SAFE_ACTIONS = [

        "restart container",

        "start container",


    ]



    def evaluate(
        self,
        decision,
        learning=None,
        safety=None,
    ):

        action = decision.get(
            "action"
        )


        if not action:

            return {

                "decision": "BLOCKED",

                "reason": [
                    "no action proposed"
                ],

                "confidence": 0,

            }



        confidence = decision.get(
            "confidence",
            0
        )


        risk = decision.get(
            "risk",
            "UNKNOWN"
        )



        similar_cases = 0

        success_rate = 0



        if learning:

            similar_cases = learning.get(
                "similar_cases",
                0
            )

            success_rate = learning.get(
                "success_rate",
                0
            )



        safety_ok = True


        if safety:

            safety_ok = safety.get(
                "allowed",
                True
            )



        if (

            action in self.SAFE_ACTIONS

            and

            confidence >= 0.8

            and

            risk == "LOW"

            and

            similar_cases > 0

            and

            success_rate >= 0.8

            and

            safety_ok

        ):

            return {

                "decision":
                    "AUTO_APPROVED",

                "confidence":
                    confidence,

                "reason": [

                    "decision confidence acceptable",

                    "low risk action",

                    f"{similar_cases} successful historical resolutions",

                    "safety validation passed",

                ],

            }



        return {

            "decision":
                "REQUIRES_APPROVAL",

            "confidence":
                confidence,

            "reason": [

                "human approval required",

            ],

        }
