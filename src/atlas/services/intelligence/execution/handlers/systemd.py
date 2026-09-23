from __future__ import annotations

import re
import subprocess

from atlas.config.operator import (
    get_executable_systemd_services,
)


_SERVICE_RE = re.compile(
    r"^[A-Za-z0-9]"
    r"[A-Za-z0-9_.@:-]{0,127}"
    r"\.service$"
)


class SystemdActionHandler:

    def __init__(
        self,
        allowed_services=None,
    ):

        self.allowed_services = frozenset(
            allowed_services
            if allowed_services is not None
            else get_executable_systemd_services()
        )

    def _validate_target(
        self,
        service,
    ):

        target = str(
            service
            or ""
        ).strip()

        if not target:

            return {
                "ok": False,
                "result": "missing service",
                "evidence": [],
            }

        if not _SERVICE_RE.fullmatch(
            target
        ):

            return {
                "ok": False,
                "result": "invalid systemd service target",
                "evidence": [],
            }

        if target not in self.allowed_services:

            return {
                "ok": False,
                "result": (
                    "systemd execution not allowed for "
                    + target
                ),
                "evidence": [
                    "systemd execution allowlist",
                ],
            }


        show = subprocess.run(
            [
                "systemctl",
                "show",
                target,
                "--property=Id",
                "--property=LoadState",
                "--value",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if show.returncode != 0:

            return {
                "ok": False,
                "result": (
                    "systemd service not found: "
                    + target
                ),
                "evidence": [],
            }


        lines = [
            line.strip()
            for line in show.stdout.splitlines()
            if line.strip()
        ]

        if len(lines) < 2:

            return {
                "ok": False,
                "result": "invalid systemd inspection result",
                "evidence": [],
            }


        canonical = lines[0]
        load_state = lines[1]

        if canonical != target:

            return {
                "ok": False,
                "result": (
                    "target must be canonical systemd service name"
                ),
                "evidence": [],
            }

        if load_state != "loaded":

            return {
                "ok": False,
                "result": (
                    "systemd service is not loaded: "
                    + target
                ),
                "evidence": [],
            }


        return {
            "ok": True,
            "target": canonical,
            "evidence": [
                "systemd target validation passed",
            ],
        }


    def _active_state(
        self,
        target,
    ):

        result = subprocess.run(
            [
                "systemctl",
                "show",
                target,
                "--property=ActiveState",
                "--value",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:

            return None

        return (
            result.stdout
            .strip()
            .lower()
        )


    def _execute(
        self,
        action,
        service,
        expected_state,
    ):

        validated = self._validate_target(
            service
        )

        if not validated["ok"]:

            return {
                "status": "FAILED",
                "result": validated["result"],
                "evidence": validated.get(
                    "evidence",
                    [],
                ),
            }


        target = validated["target"]

        evidence = list(
            validated.get(
                "evidence",
                [],
            )
        )


        try:

            execution = subprocess.run(
                [
                    "systemctl",
                    action,
                    target,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if execution.returncode != 0:

                return {
                    "status": "FAILED",
                    "result": (
                        execution.stderr.strip()
                        or execution.stdout.strip()
                        or (
                            "systemctl "
                            + action
                            + " failed"
                        )
                    ),
                    "evidence": evidence,
                }


            evidence.append(
                f"systemctl {action} executed for {target}"
            )


            state = self._active_state(
                target
            )

            evidence.append(
                "systemd ActiveState="
                + str(state)
            )


            if state != expected_state:

                return {
                    "status": "FAILED",
                    "result": (
                        "service verification failed: "
                        + str(state)
                    ),
                    "evidence": evidence,
                }


            evidence.append(
                "systemd state verification passed"
            )


            return {
                "status": "SUCCESS",
                "result": target,
                "evidence": evidence,
            }


        except Exception as exc:

            return {
                "status": "FAILED",
                "result": str(exc),
                "evidence": evidence,
            }


    def start_service(
        self,
        service,
    ):

        return self._execute(
            "start",
            service,
            "active",
        )


    def restart_service(
        self,
        service,
    ):

        return self._execute(
            "restart",
            service,
            "active",
        )


    def stop_service(
        self,
        service,
    ):

        return self._execute(
            "stop",
            service,
            "inactive",
        )
