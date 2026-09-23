from types import SimpleNamespace

from atlas.services.intelligence.execution.handlers.docker import (
    DockerActionHandler,
)
from atlas.services.intelligence.execution.validators import (
    ActionValidator,
)
from atlas.services.intelligence.safety.service import (
    ActionSafetyService,
)


def test_stop_container_is_allowed_by_execution_validator():

    result = (
        ActionValidator()
        .validate(
            "stop container"
        )
    )

    assert result["valid"] is True


def test_stop_container_is_medium_risk_and_requires_approval():

    incident = SimpleNamespace(
        incident_id="OP-STOP-TEST",
        asset="flaresolverr",
        diagnosis={},
        recommendation={
            "action":
                "stop container",

            "incident_id":
                "OP-STOP-TEST",

            "evidence": [],
        },
    )

    result = (
        ActionSafetyService()
        .evaluate(
            incident
        )
    )

    assert (
        result["status"]
        == "PENDING_APPROVAL"
    )

    assert (
        result["risk"]
        == "MEDIUM"
    )

    assert (
        result["requires_approval"]
        is True
    )

    assert (
        result["rollback"]
        == "docker start flaresolverr"
    )


def test_stop_container_executes_and_verifies_stopped(
    monkeypatch,
):

    calls = []

    responses = [
        SimpleNamespace(
            returncode=0,
            stdout="flaresolverr\n",
            stderr="",
        ),
        SimpleNamespace(
            returncode=0,
            stdout="false\n",
            stderr="",
        ),
    ]

    def fake_run(
        command,
        **kwargs,
    ):

        calls.append(
            command
        )

        return responses.pop(0)


    monkeypatch.setattr(
        (
            "atlas.services.intelligence."
            "execution.handlers.docker."
            "subprocess.run"
        ),
        fake_run,
    )


    result = (
        DockerActionHandler()
        .stop_container(
            "flaresolverr"
        )
    )


    assert (
        result["status"]
        == "SUCCESS"
    )

    assert calls[0] == [
        "docker",
        "stop",
        "flaresolverr",
    ]

    assert calls[1] == [
        "docker",
        "inspect",
        "-f",
        "{{.State.Running}}",
        "flaresolverr",
    ]

    assert (
        "container stopped verification passed"
        in result["evidence"]
    )


def test_stop_container_fails_when_still_running(
    monkeypatch,
):

    responses = [
        SimpleNamespace(
            returncode=0,
            stdout="flaresolverr\n",
            stderr="",
        ),
        SimpleNamespace(
            returncode=0,
            stdout="true\n",
            stderr="",
        ),
    ]

    def fake_run(
        command,
        **kwargs,
    ):
        return responses.pop(0)


    monkeypatch.setattr(
        (
            "atlas.services.intelligence."
            "execution.handlers.docker."
            "subprocess.run"
        ),
        fake_run,
    )


    result = (
        DockerActionHandler()
        .stop_container(
            "flaresolverr"
        )
    )


    assert (
        result["status"]
        == "FAILED"
    )

    assert (
        result["result"]
        == "container running after stop"
    )
