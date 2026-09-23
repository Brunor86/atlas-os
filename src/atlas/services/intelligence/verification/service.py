from __future__ import annotations

from datetime import (
    UTC,
    datetime,
)

import subprocess

from atlas.services.proxmox import (
    ProxmoxService,
)


class ActionVerificationService:
    """
    Independent post-execution verification.

    Execution handlers already perform immediate backend checks.
    This service deliberately performs a second read after command
    execution so ATLAS can persist a distinct verification outcome.

    Verification is read-only.
    """

    _EXPECTED = {
        "start container":
            (
                "docker",
                "running",
                None,
            ),

        "restart container":
            (
                "docker",
                "running",
                None,
            ),

        "stop container":
            (
                "docker",
                "stopped",
                None,
            ),

        "start service":
            (
                "systemd",
                "active",
                None,
            ),

        "restart service":
            (
                "systemd",
                "active",
                None,
            ),

        "stop service":
            (
                "systemd",
                "inactive",
                None,
            ),

        "start vm":
            (
                "proxmox",
                "running",
                "qemu",
            ),

        "restart vm":
            (
                "proxmox",
                "running",
                "qemu",
            ),

        "stop vm":
            (
                "proxmox",
                "stopped",
                "qemu",
            ),

        "restart lxc":
            (
                "proxmox",
                "running",
                "lxc",
            ),
    }


    def __init__(
        self,
        runner=None,
        proxmox=None,
    ):

        self.runner = (
            runner
            or subprocess.run
        )

        #
        # Proxmox is deliberately lazy.
        # Docker-only execution must not require Proxmox
        # configuration merely to construct the verifier.
        #
        self.proxmox = proxmox


    def _docker_state(
        self,
        target,
    ):

        result = self.runner(
            [
                "docker",
                "inspect",
                "-f",
                "{{.State.Running}}",
                str(target),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:

            return (
                "unknown",
                (
                    result.stderr.strip()
                    or "docker inspect failed"
                ),
            )


        running = (
            result.stdout
            .strip()
            .lower()
            == "true"
        )


        return (
            (
                "running"
                if running
                else "stopped"
            ),
            "",
        )


    def _systemd_state(
        self,
        target,
    ):

        result = self.runner(
            [
                "systemctl",
                "show",
                str(target),
                "--property=ActiveState",
                "--value",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:

            return (
                "unknown",
                (
                    result.stderr.strip()
                    or "systemd state inspection failed"
                ),
            )


        value = (
            result.stdout
            .strip()
            .lower()
        )


        return (
            value
            or "unknown",
            "",
        )


    def _proxmox_state(
        self,
        target,
        guest_type,
    ):

        proxmox = self.proxmox

        if proxmox is None:

            proxmox = (
                ProxmoxService()
            )


        try:

            vmid = int(
                str(
                    target
                ).strip()
            )

            guest = (
                proxmox.resolve_guest(
                    vmid,
                    expected_type=guest_type,
                )
            )

        except Exception as exc:

            return (
                "unknown",
                str(exc),
            )


        return (
            str(
                guest.status
                or "unknown"
            ).lower(),
            "",
        )


    def verify(
        self,
        action,
        target,
    ):

        normalized = str(
            action
            or ""
        ).strip().lower()

        route = (
            self._EXPECTED.get(
                normalized
            )
        )


        verified_at = (
            datetime.now(
                UTC
            ).isoformat()
        )


        if route is None:

            return {
                "status":
                    "RECOVERY_REQUIRED",

                "action":
                    normalized,

                "target":
                    str(
                        target
                        or ""
                    ),

                "expected_state":
                    "known verification route",

                "observed_state":
                    "unsupported",

                "detail":
                    (
                        "post-execution verification "
                        "route is unavailable"
                    ),

                "evidence": [
                    "verification fails closed",
                ],

                "verified_at":
                    verified_at,
            }


        backend, expected, guest_type = route


        try:

            if backend == "docker":

                observed, error = (
                    self._docker_state(
                        target
                    )
                )


            elif backend == "systemd":

                observed, error = (
                    self._systemd_state(
                        target
                    )
                )


            elif backend == "proxmox":

                observed, error = (
                    self._proxmox_state(
                        target,
                        guest_type,
                    )
                )


            else:

                observed = "unknown"
                error = (
                    "verification backend unavailable"
                )


        except Exception as exc:

            observed = "unknown"
            error = str(exc)


        evidence = [
            (
                "post-execution backend="
                + backend
            ),
            (
                "expected_state="
                + expected
            ),
            (
                "observed_state="
                + str(
                    observed
                )
            ),
        ]


        if error:

            evidence.append(
                "verification_error="
                + error
            )


        if observed == expected:

            return {
                "status":
                    "VERIFIED",

                "action":
                    normalized,

                "target":
                    str(
                        target
                        or ""
                    ),

                "expected_state":
                    expected,

                "observed_state":
                    observed,

                "detail":
                    (
                        "post-execution verification "
                        "passed"
                    ),

                "evidence":
                    evidence,

                "verified_at":
                    verified_at,
            }


        return {
            "status":
                "RECOVERY_REQUIRED",

            "action":
                normalized,

            "target":
                str(
                    target
                    or ""
                ),

            "expected_state":
                expected,

            "observed_state":
                observed,

            "detail":
                (
                    "post-execution verification failed: "
                    "expected "
                    + expected
                    + ", observed "
                    + str(
                        observed
                    )
                ),

            "evidence":
                evidence,

            "verified_at":
                verified_at,
        }
