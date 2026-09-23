from atlas.api.stream_status import (
    completed_status,
)


def test_completed_status_uses_agent_success():

    assert completed_status(
        {
            "agent_status":
                "SUCCESS",
        }
    ) == "SUCCESS"


def test_completed_status_preserves_agent_error():

    assert completed_status(
        {
            "agent_status":
                "ERROR",
        }
    ) == "ERROR"


def test_completed_status_preserves_max_steps():

    assert completed_status(
        {
            "agent_status":
                "MAX_STEPS",
        }
    ) == "MAX_STEPS"


def test_completed_status_falls_back_for_legacy_metadata():

    assert completed_status(
        {}
    ) == "SUCCESS"
