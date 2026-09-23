from types import SimpleNamespace

from atlas.services.intelligence.execution.handlers.systemd import (
    SystemdActionHandler,
)
from atlas.services.intelligence.execution.validators import (
    ActionValidator,
)
from atlas.services.intelligence.safety.service import (
    ActionSafetyService,
)


class FakeCompleted:

    def __init__(
        self,
        returncode=0,
        stdout="",
        stderr="",
    ):

        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_validator_allows_service_actions():

    validator = ActionValidator()

    for action in (
        "start service",
        "restart service",
        "stop service",
    ):

        assert validator.validate(
            action
        )["valid"] is True


def test_service_safety_contract():

    incident = SimpleNamespace(
        incident_id="OP-SERVICE-TEST",
        asset="atlas-collector.service",
        diagnosis={},
        recommendation={
            "action":
                "stop service",

            "incident_id":
                "OP-SERVICE-TEST",

            "evidence": [],
        },
    )

    result = (
        ActionSafetyService()
        .evaluate(
            incident
        )
    )

    assert result["status"] == "PENDING_APPROVAL"
    assert result["risk"] == "MEDIUM"
    assert result["requires_approval"] is True

    assert (
        result["rollback"]
        == "systemctl start atlas-collector.service"
    )


def test_restart_service_executes_and_verifies(
    monkeypatch,
):

    calls = []

    def fake_run(
        args,
        **kwargs,
    ):

        calls.append(
            list(args)
        )

        if args[:2] == [
            "systemctl",
            "show",
        ]:

            if (
                "--property=Id"
                in args
            ):

                return FakeCompleted(
                    stdout=(
                        "atlas-collector.service\n"
                        "loaded\n"
                    )
                )

            if (
                "--property=ActiveState"
                in args
            ):

                return FakeCompleted(
                    stdout="active\n"
                )

        if args[:2] == [
            "systemctl",
            "restart",
        ]:

            return FakeCompleted()

        raise AssertionError(
            args
        )


    monkeypatch.setattr(
        "atlas.services.intelligence.execution.handlers.systemd.subprocess.run",
        fake_run,
    )


    result = (
        SystemdActionHandler(allowed_services={"atlas-collector.service"})
        .restart_service(
            "atlas-collector.service"
        )
    )


    assert result["status"] == "SUCCESS"

    assert [
        "systemctl",
        "restart",
        "atlas-collector.service",
    ] in calls


def test_systemd_execution_blocks_non_allowlisted_service():

    result = (
        SystemdActionHandler(allowed_services={"atlas-collector.service"})
        .restart_service(
            "atlas-web.service"
        )
    )

    assert result["status"] == "FAILED"

    assert (
        "not allowed"
        in result["result"]
    )


def test_stop_service_requires_inactive_verification(
    monkeypatch,
):

    def fake_run(
        args,
        **kwargs,
    ):

        if args[:2] == [
            "systemctl",
            "show",
        ]:

            if (
                "--property=Id"
                in args
            ):

                return FakeCompleted(
                    stdout=(
                        "atlas-collector.service\n"
                        "loaded\n"
                    )
                )

            if (
                "--property=ActiveState"
                in args
            ):

                return FakeCompleted(
                    stdout="inactive\n"
                )

        if args[:2] == [
            "systemctl",
            "stop",
        ]:

            return FakeCompleted()

        raise AssertionError(
            args
        )


    monkeypatch.setattr(
        "atlas.services.intelligence.execution.handlers.systemd.subprocess.run",
        fake_run,
    )


    result = (
        SystemdActionHandler(allowed_services={"atlas-collector.service"})
        .stop_service(
            "atlas-collector.service"
        )
    )

    assert result["status"] == "SUCCESS"
