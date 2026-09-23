from atlas.services.ai.reasoning import AIReasoningEngine



def test_no_incidents_returns_low_priority():

    engine = AIReasoningEngine()


    context = {

        "incidents": [],

        "recommendations": [],

    }


    result = engine.analyze(
        context
    )


    assert result["priority"] == "LOW"

    assert result["confidence"] == 0.9



def test_infrastructure_degradation_returns_medium():

    engine = AIReasoningEngine()


    context = {

        "incidents": [

            {

                "name":
                    "infrastructure_degradation"

            }

        ],

        "recommendations": [],

    }


    result = engine.analyze(
        context
    )


    assert result["priority"] == "MEDIUM"

    assert (
        "Operational service degradation detected"
        in result["reasoning"]
    )



def test_storage_risk_returns_high():

    engine = AIReasoningEngine()


    context = {

        "incidents": [

            {

                "name":
                    "storage_risk"

            }

        ],

        "recommendations": [

            {

                "actions":

                    [

                        "Check disk capacity"

                    ]

            }

        ],

    }


    result = engine.analyze(
        context
    )


    assert result["priority"] == "HIGH"

    assert (
        "Storage capacity risk detected"
        in result["reasoning"]
    )

    assert (
        "Check disk capacity"
        in result["actions"]
    )
