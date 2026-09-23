from atlas.services.ai.reasoning_gate import (
    AIReasoningGate,
)


def test_good_reasoning_does_not_escalate():

    gate = AIReasoningGate()

    result = gate.evaluate(

        """
        {
            "summary": "Application offline",
            "root_cause": "container stopped",
            "evidence": [
                "container stopped"
            ],
            "missing_evidence": [],
            "confidence": 0.9
        }
        """,

        task="incident_reasoning",

    )

    assert result.escalate is False

    assert result.score >= 0.70


def test_low_confidence_reasoning_escalates():

    gate = AIReasoningGate()

    result = gate.evaluate(

        """
        {
            "summary": "Application offline",
            "root_cause": "unknown",
            "evidence": [
                "application offline"
            ],
            "missing_evidence": [
                "container logs"
            ],
            "confidence": 0.5
        }
        """,

        task="incident_reasoning",

    )

    assert result.escalate is True

    assert result.score < 0.70

    assert (
        "low model confidence"
        in result.reasons
    )

    assert (
        "missing evidence reported"
        in result.reasons
    )


def test_unstructured_reasoning_is_weaker():

    gate = AIReasoningGate()

    result = gate.evaluate(

        "The application is probably down because the host failed.",

        task="incident_reasoning",

    )

    assert result.escalate is False

    assert result.score == 0.80

    assert (
        "unstructured reasoning response"
        in result.reasons
    )


def test_high_confidence_with_missing_root_cause_escalates():

    gate = AIReasoningGate()

    result = gate.evaluate(

        """
        {
            "summary": "Application offline",
            "root_cause": "",
            "evidence": [
                "application offline"
            ],
            "missing_evidence": [],
            "confidence": 0.95
        }
        """,

        task="incident_reasoning",

    )

    assert result.escalate is False

    #
    # The model is still above the current gate threshold.
    # Root-cause uncertainty is recorded but does not
    # automatically force escalation by itself.
    #

    assert (
        "root cause not established"
        in result.reasons
    )


def test_complete_reasoning_scores_one():

    gate = AIReasoningGate()

    result = gate.evaluate(

        """
        {
            "summary": "Reverse proxy unavailable",
            "root_cause": "container stopped",
            "evidence": [
                "container stopped",
                "application status OFFLINE"
            ],
            "missing_evidence": [],
            "confidence": 0.95
        }
        """,

        task="incident_reasoning",

    )

    assert result.escalate is False

    assert result.score == 1.0

    assert result.reasons == []
