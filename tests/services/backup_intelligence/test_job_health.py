import subprocess

from atlas.services.backup_intelligence.job_health import (
    BackupJobStatus,
    SystemdJobHealthService,
)


TIMER_OK = """LoadState=loaded
ActiveState=active
UnitFileState=enabled
LastTriggerUSec=Fri 2026-09-25 03:30:02 -03
NextElapseUSecRealtime=Sat 2026-09-26 03:30:00 -03
"""

SERVICE_OK = """LoadState=loaded
Result=success
ExecMainStatus=0
ExecMainStartTimestamp=Fri 2026-09-25 03:30:02 -03
ExecMainExitTimestamp=Fri 2026-09-25 03:30:06 -03
"""


def fake_runner(
    command,
    capture_output,
    text,
    timeout,
    check,
):
    output = (
        TIMER_OK
        if any(
            str(value).endswith(".timer")
            for value in command
        )
        else SERVICE_OK
    )

    return subprocess.CompletedProcess(
        command,
        0,
        stdout=output,
        stderr="",
    )


def test_local_systemd_job_is_healthy():

    observer = SystemdJobHealthService(
        providers={
            "local": {
                "type": "systemd-local",
            }
        },
        runner=fake_runner,
    )

    result = observer.evaluate(
        "local",
        "atlas-backup-local.timer",
    )

    assert result.status == BackupJobStatus.HEALTHY
    assert result.service == "atlas-backup-local.service"


def test_ssh_systemd_job_uses_read_only_batch_mode():

    calls = []

    def runner(
        command,
        capture_output,
        text,
        timeout,
        check,
    ):
        calls.append(command)

        return fake_runner(
            command,
            capture_output,
            text,
            timeout,
            check,
        )

    observer = SystemdJobHealthService(
        providers={
            "proxmox": {
                "type": "systemd-ssh",
                "target": "root@192.168.1.86",
            }
        },
        runner=runner,
    )

    result = observer.evaluate(
        "proxmox",
        "atlas-proxmox-config-backup.timer",
    )

    assert result.status == BackupJobStatus.HEALTHY

    assert calls[0][:6] == [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=5",
        "root@192.168.1.86",
    ]

    flattened = " ".join(
        value
        for command in calls
        for value in command
    )

    for forbidden in (
        " start ",
        " stop ",
        " restart ",
        " enable ",
        " disable ",
    ):
        assert forbidden not in (
            " " + flattened + " "
        )


def test_not_found_timer_is_failed_even_if_service_result_is_success():

    def runner(
        command,
        capture_output,
        text,
        timeout,
        check,
    ):
        timer = any(
            str(value).endswith(".timer")
            for value in command
        )

        output = (
            """LoadState=not-found
ActiveState=inactive
UnitFileState=
"""
            if timer
            else SERVICE_OK
        )

        return subprocess.CompletedProcess(
            command,
            0,
            stdout=output,
            stderr="",
        )

    observer = SystemdJobHealthService(
        providers={
            "local": {
                "type": "systemd-local",
            }
        },
        runner=runner,
    )

    result = observer.evaluate(
        "local",
        "missing-backup.timer",
    )

    assert result.status == BackupJobStatus.FAILED
    assert "not loaded" in result.detail


def test_transport_failure_is_unobserved_not_failed():

    def runner(
        command,
        capture_output,
        text,
        timeout,
        check,
    ):
        return subprocess.CompletedProcess(
            command,
            255,
            stdout="",
            stderr="connection unavailable",
        )

    observer = SystemdJobHealthService(
        providers={
            "proxmox": {
                "type": "systemd-ssh",
                "target": "root@192.168.1.86",
            }
        },
        runner=runner,
    )

    result = observer.evaluate(
        "proxmox",
        "atlas-proxmox-guest-backup.timer",
    )

    assert result.status == BackupJobStatus.UNOBSERVED
