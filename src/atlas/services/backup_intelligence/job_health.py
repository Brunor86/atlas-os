import re
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable


class BackupJobStatus(StrEnum):
    HEALTHY = "HEALTHY"
    FAILED = "FAILED"
    UNOBSERVED = "UNOBSERVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(slots=True)
class BackupJobHealth:
    status: BackupJobStatus
    provider: str | None
    timer: str | None
    service: str | None
    detail: str

    def as_dict(self) -> dict:
        return {
            "status": self.status.value,
            "provider": self.provider,
            "timer": self.timer,
            "service": self.service,
            "detail": self.detail,
        }


class SystemdJobHealthService:
    """Read-only observer for local or SSH systemd jobs."""

    _UNIT_RE = re.compile(
        r"^[A-Za-z0-9_.@:-]+\.(?:timer|service)$"
    )
    _TARGET_RE = re.compile(
        r"^[A-Za-z0-9_.@:-]+$"
    )

    def __init__(
        self,
        providers: dict | None = None,
        runner: Callable[..., subprocess.CompletedProcess] | None = None,
        timeout_seconds: float = 7.0,
    ):
        self.providers = (
            providers
            if isinstance(providers, dict)
            else {}
        )
        self._runner = runner or subprocess.run
        self.timeout_seconds = timeout_seconds

    def evaluate(
        self,
        provider_name: str | None,
        timer: str | None,
    ) -> BackupJobHealth:
        if not timer:
            return self._result(
                BackupJobStatus.NOT_APPLICABLE,
                provider_name,
                None,
                None,
                "no observable timer configured",
            )

        service = self._service_name(timer)

        if not self._safe_unit(timer):
            return self._result(
                BackupJobStatus.UNOBSERVED,
                provider_name,
                timer,
                service,
                "timer name rejected by read-only observer",
            )

        provider = self.providers.get(
            provider_name or ""
        )

        if not isinstance(provider, dict):
            return self._result(
                BackupJobStatus.UNOBSERVED,
                provider_name,
                timer,
                service,
                "job provider is not configured",
            )

        provider_type = str(
            provider.get("type", "")
            or ""
        ).strip()

        try:
            timer_state = self._show(
                provider,
                provider_type,
                timer,
                (
                    "LoadState",
                    "ActiveState",
                    "UnitFileState",
                    "LastTriggerUSec",
                    "NextElapseUSecRealtime",
                ),
            )
            service_state = self._show(
                provider,
                provider_type,
                service,
                (
                    "LoadState",
                    "Result",
                    "ExecMainStatus",
                    "ExecMainStartTimestamp",
                    "ExecMainExitTimestamp",
                ),
            )
        except (
            OSError,
            subprocess.SubprocessError,
        ) as exc:
            return self._result(
                BackupJobStatus.UNOBSERVED,
                provider_name,
                timer,
                service,
                (
                    "job provider could not be observed: "
                    f"{type(exc).__name__}"
                ),
            )

        if timer_state.get("LoadState") != "loaded":
            return self._result(
                BackupJobStatus.FAILED,
                provider_name,
                timer,
                service,
                "configured timer is not loaded",
            )

        if timer_state.get("ActiveState") != "active":
            return self._result(
                BackupJobStatus.FAILED,
                provider_name,
                timer,
                service,
                "configured timer is not active",
            )

        unit_file_state = timer_state.get(
            "UnitFileState",
            "",
        )

        if unit_file_state not in {
            "enabled",
            "enabled-runtime",
            "linked",
            "linked-runtime",
        }:
            return self._result(
                BackupJobStatus.FAILED,
                provider_name,
                timer,
                service,
                (
                    "configured timer is not enabled "
                    f"({unit_file_state or 'unknown'})"
                ),
            )

        if service_state.get("LoadState") != "loaded":
            return self._result(
                BackupJobStatus.FAILED,
                provider_name,
                timer,
                service,
                "configured service is not loaded",
            )

        result = service_state.get(
            "Result",
            "",
        )
        exit_status = service_state.get(
            "ExecMainStatus",
            "",
        )

        if result and result != "success":
            return self._result(
                BackupJobStatus.FAILED,
                provider_name,
                timer,
                service,
                f"last service result is {result}",
            )

        if exit_status not in {
            "",
            "0",
        }:
            return self._result(
                BackupJobStatus.FAILED,
                provider_name,
                timer,
                service,
                (
                    "last service exit status is "
                    f"{exit_status}"
                ),
            )

        return self._result(
            BackupJobStatus.HEALTHY,
            provider_name,
            timer,
            service,
            (
                "timer is active and enabled; "
                "last service result is healthy"
            ),
        )

    def _show(
        self,
        provider: dict,
        provider_type: str,
        unit: str,
        properties: tuple[str, ...],
    ) -> dict[str, str]:
        command = self._command(
            provider,
            provider_type,
            unit,
            properties,
        )

        result = self._runner(
            command,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )

        if result.returncode not in {
            0,
            1,
        }:
            raise subprocess.SubprocessError(
                "systemd observation command failed"
            )

        return self._parse_show(
            result.stdout
        )

    def _command(
        self,
        provider: dict,
        provider_type: str,
        unit: str,
        properties: tuple[str, ...],
    ) -> list[str]:
        base = [
            "systemctl",
            "show",
            unit,
        ]

        for key in properties:
            base.extend(
                [
                    "-p",
                    key,
                ]
            )

        base.append("--no-pager")

        if provider_type == "systemd-local":
            return base

        if provider_type == "systemd-ssh":
            target = str(
                provider.get("target", "")
                or ""
            ).strip()

            if not self._safe_target(target):
                raise OSError(
                    "invalid SSH target"
                )

            return [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=5",
                target,
                *base,
            ]

        raise OSError(
            "unsupported job provider"
        )

    @staticmethod
    def _parse_show(
        output: str,
    ) -> dict[str, str]:
        values = {}

        for line in output.splitlines():
            key, separator, value = (
                line.partition("=")
            )
            if separator:
                values[key] = value

        return values

    @classmethod
    def _safe_unit(
        cls,
        unit: str,
    ) -> bool:
        value = str(unit)

        return (
            not value.startswith("-")
            and bool(
                cls._UNIT_RE.fullmatch(
                    value
                )
            )
        )

    @classmethod
    def _safe_target(
        cls,
        target: str,
    ) -> bool:
        value = str(target)

        return (
            not value.startswith("-")
            and bool(
                cls._TARGET_RE.fullmatch(
                    value
                )
            )
        )

    @staticmethod
    def _service_name(
        timer: str,
    ) -> str:
        if str(timer).endswith(".timer"):
            return (
                str(timer)[:-6]
                + ".service"
            )

        return str(timer)

    @staticmethod
    def _result(
        status: BackupJobStatus,
        provider: str | None,
        timer: str | None,
        service: str | None,
        detail: str,
    ) -> BackupJobHealth:
        return BackupJobHealth(
            status=status,
            provider=provider,
            timer=timer,
            service=service,
            detail=detail,
        )
