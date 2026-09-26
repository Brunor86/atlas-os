from __future__ import annotations

import re
import time
from urllib.parse import quote

from atlas.services.proxmox import (
    ProxmoxService,
)

from atlas.config.operator import (
    get_executable_qemu_vmids,
    get_executable_lxc_vmids,
)


_VMID_RE = re.compile(
    r"^[1-9][0-9]{0,8}$"
)


class ProxmoxActionHandler:

    def __init__(
        self,
        proxmox=None,
        poll_attempts=20,
        poll_interval=0.5,
        allowed_qemu_vmids=None,
        allowed_lxc_vmids=None,
    ):

        self.proxmox = (
            proxmox
            or ProxmoxService()
        )

        self.poll_attempts = (
            poll_attempts
        )

        self.poll_interval = (
            poll_interval
        )

        self.allowed_qemu_vmids = frozenset(
            allowed_qemu_vmids
            if allowed_qemu_vmids is not None
            else get_executable_qemu_vmids()
        )

        self.allowed_lxc_vmids = frozenset(
            allowed_lxc_vmids
            if allowed_lxc_vmids is not None
            else get_executable_lxc_vmids()
        )


    def _validate_target(
        self,
        target,
    ):

        raw = str(
            target
            or ""
        ).strip()

        if not _VMID_RE.fullmatch(
            raw
        ):

            return {
                "ok": False,
                "result":
                    "invalid Proxmox VMID",
                "evidence": [],
            }


        vmid = int(
            raw
        )

        if vmid not in self.allowed_qemu_vmids:

            return {
                "ok": False,
                "result": (
                    "Proxmox execution "
                    "not allowed for VMID "
                    + str(vmid)
                ),
                "evidence": [
                    "Proxmox execution allowlist",
                ],
            }


        try:

            guest = (
                self.proxmox
                .resolve_guest(
                    vmid,
                    expected_type="qemu",
                )
            )

        except Exception as exc:

            return {
                "ok": False,
                "result": str(
                    exc
                ),
                "evidence": [],
            }


        return {
            "ok": True,
            "vmid": vmid,
            "guest": guest,
            "evidence": [
                (
                    "Proxmox target "
                    "validation passed"
                ),
                (
                    "VMID="
                    + str(
                        guest.vmid
                    )
                ),
                (
                    "node="
                    + guest.node
                ),
                (
                    "guest="
                    + guest.name
                ),
            ],
        }

    def _validate_lxc_target(
        self,
        target,
    ):

        raw = str(
            target
            or ""
        ).strip()

        if not _VMID_RE.fullmatch(
            raw
        ):

            return {
                "ok": False,
                "result":
                    "invalid Proxmox VMID",
                "evidence": [],
            }

        vmid = int(
            raw
        )

        if vmid not in self.allowed_lxc_vmids:

            return {
                "ok": False,
                "result": (
                    "Proxmox execution "
                    "not allowed for VMID "
                    + str(vmid)
                ),
                "evidence": [
                    "Proxmox execution allowlist",
                ],
            }

        try:

            guest = (
                self.proxmox
                .resolve_guest(
                    vmid,
                    expected_type="lxc",
                )
            )

        except Exception as exc:

            return {
                "ok": False,
                "result": str(
                    exc
                ),
                "evidence": [],
            }

        return {
            "ok": True,
            "vmid": vmid,
            "guest": guest,
            "evidence": [
                "Proxmox target validation passed",
                (
                    "VMID="
                    + str(
                        guest.vmid
                    )
                ),
                (
                    "node="
                    + guest.node
                ),
                (
                    "guest="
                    + guest.name
                ),
            ],
        }


    def _wait_for_state(
        self,
        vmid,
        expected_state,
        *,
        guest_type="qemu",
    ):

        last_state = None

        for attempt in range(
            self.poll_attempts
        ):

            guest = (
                self.proxmox
                .resolve_guest(
                    vmid,
                    expected_type=guest_type,
                )
            )

            last_state = (
                guest.status
            )

            if (
                last_state
                == expected_state
            ):

                return last_state

            if (
                attempt
                < self.poll_attempts - 1
                and self.poll_interval > 0
            ):

                time.sleep(
                    self.poll_interval
                )

        return last_state

    def _wait_for_task(
        self,
        node,
        task,
    ):

        if not task:
            return None

        encoded_upid = quote(
            str(task),
            safe="",
        )

        endpoint = (
            "/api2/json/nodes/"
            + str(node)
            + "/tasks/"
            + encoded_upid
            + "/status"
        )

        last_task = None

        for attempt in range(
            self.poll_attempts
        ):

            task_status = (
                self.proxmox
                ._get(
                    endpoint
                )
            )

            if not isinstance(
                task_status,
                dict,
            ):

                task_status = {}

            last_task = (
                task_status
            )

            status = (
                task_status.get(
                    "status"
                )
            )

            if status == "stopped":
                return task_status

            if (
                status is not None
                and status != "running"
            ):

                return task_status

            if (
                attempt
                < self.poll_attempts - 1
                and self.poll_interval > 0
            ):

                time.sleep(
                    self.poll_interval
                )

        return (
            last_task
            or None
        )


    def start_vm(
        self,
        target,
    ):

        validated = (
            self._validate_target(
                target
            )
        )

        if not validated[
            "ok"
        ]:

            return {
                "status": "FAILED",
                "result":
                    validated[
                        "result"
                    ],
                "evidence":
                    validated.get(
                        "evidence",
                        [],
                    ),
            }


        vmid = validated[
            "vmid"
        ]

        guest = validated[
            "guest"
        ]

        evidence = list(
            validated.get(
                "evidence",
                [],
            )
        )

        evidence.append(
            "current_state="
            + guest.status
        )


        if guest.status == "running":

            return {
                "status": "FAILED",
                "result": (
                    "Proxmox VM "
                    + str(vmid)
                    + " is already running"
                ),
                "evidence": evidence,
            }


        if guest.status != "stopped":

            return {
                "status": "FAILED",
                "result": (
                    "Proxmox VM "
                    + str(vmid)
                    + " cannot be started "
                    "from state "
                    + guest.status
                ),
                "evidence": evidence,
            }


        try:

            conflicts = (
                self.proxmox
                .running_qemu_pci_conflicts(
                    vmid
                )
            )

        except Exception as exc:

            return {
                "status": "FAILED",
                "result": (
                    "Proxmox PCI safety "
                    "check failed: "
                    + str(exc)
                ),
                "evidence": evidence,
            }


        if conflicts:

            for conflict in conflicts:

                evidence.append(
                    (
                        "PCI conflict: "
                        "VMID="
                        + str(
                            conflict[
                                "vmid"
                            ]
                        )
                        + " guest="
                        + conflict[
                            "name"
                        ]
                        + " devices="
                        + ",".join(
                            conflict[
                                "devices"
                            ]
                        )
                    )
                )

            return {
                "status": "FAILED",
                "result": (
                    "Proxmox PCI conflict "
                    "blocks start of VM "
                    + str(vmid)
                ),
                "evidence": evidence,
            }


        evidence.append(
            "PCI conflict check passed"
        )


        endpoint = (
            "/api2/json/nodes/"
            + guest.node
            + "/qemu/"
            + str(vmid)
            + "/status/start"
        )


        try:

            task = (
                self.proxmox
                ._post(
                    endpoint
                )
            )

        except Exception as exc:

            return {
                "status": "FAILED",
                "result": (
                    "Proxmox start "
                    "request failed: "
                    + str(exc)
                ),
                "evidence": evidence,
            }


        evidence.append(
            (
                "Proxmox start requested "
                "for VMID="
                + str(vmid)
            )
        )

        if task:

            evidence.append(
                "Proxmox task="
                + str(task)
            )


        try:

            state = (
                self._wait_for_state(
                    vmid,
                    "running",
                )
            )

        except Exception as exc:

            return {
                "status": "FAILED",
                "result": (
                    "Proxmox state "
                    "verification failed: "
                    + str(exc)
                ),
                "evidence": evidence,
            }


        evidence.append(
            "verified_state="
            + str(state)
        )


        if state != "running":

            return {
                "status": "FAILED",
                "result": (
                    "Proxmox VM start "
                    "verification failed: "
                    + str(state)
                ),
                "evidence": evidence,
            }


        evidence.append(
            "Proxmox VM state verification passed"
        )


        return {
            "status": "SUCCESS",
            "result": (
                "VM "
                + str(vmid)
                + " running"
            ),
            "evidence": evidence,
        }


    def stop_vm(self, target):
        validated = self._validate_target(target)
        if not validated['ok']:
            return {'status': 'FAILED', 'result': validated['result'], 'evidence': validated.get('evidence', [])}
        vmid = validated['vmid']
        guest = validated['guest']
        evidence = list(validated.get('evidence', []))
        evidence.append('current_state=' + guest.status)
        if guest.status == 'stopped':
            return {'status': 'FAILED', 'result': f'Proxmox VM {vmid} is already stopped', 'evidence': evidence}
        if guest.status != 'running':
            return {'status': 'FAILED', 'result': f'Proxmox VM {vmid} cannot be stopped from state {guest.status}', 'evidence': evidence}
        endpoint = '/api2/json/nodes/' + guest.node + '/qemu/' + str(vmid) + '/status/stop'
        try:
            task = self.proxmox._post(endpoint)
        except Exception as exc:
            return {'status': 'FAILED', 'result': f'Proxmox stop request failed: {str(exc)}', 'evidence': evidence}
        evidence.append(f'Proxmox stop requested for VMID={vmid}')
        if task:
            evidence.append('Proxmox task=' + str(task))
        try:
            state = self._wait_for_state(vmid, 'stopped')
        except Exception as exc:
            return {'status': 'FAILED', 'result': f'Proxmox state verification failed: {str(exc)}', 'evidence': evidence}
        evidence.append('verified_state=' + str(state))
        if state != 'stopped':
            return {'status': 'FAILED', 'result': f'Proxmox VM stop verification failed: {state}', 'evidence': evidence}
        evidence.append('Proxmox VM state verification passed')
        return {'status': 'SUCCESS', 'result': f'VM {vmid} stopped', 'evidence': evidence}


    def restart_vm(self, target):
        stop_res = self.stop_vm(target)
        if stop_res.get('status') != 'SUCCESS':
            return {'status': 'FAILED', 'result': f"Stop phase failed: {stop_res.get('result')}", 'evidence': stop_res.get('evidence', []) + ['restart aborted due to stop failure']}
        start_res = self.start_vm(target)
        if start_res.get('status') != 'SUCCESS':
            combined_evidence = stop_res.get('evidence', []) + ['stop phase succeeded'] + start_res.get('evidence', [])
            return {'status': 'FAILED', 'result': f"Start phase failed: {start_res.get('result')}", 'evidence': combined_evidence}
        combined_evidence = stop_res.get('evidence', []) + ['stop phase succeeded'] + start_res.get('evidence', [])
        return {'status': 'SUCCESS', 'result': f'VM {target} restarted successfully', 'evidence': combined_evidence}

    def start_lxc(
        self,
        target,
    ):

        validated = (
            self._validate_lxc_target(
                target
            )
        )

        if not validated[
            "ok"
        ]:

            return {
                "status": "FAILED",
                "result":
                    validated[
                        "result"
                    ],
                "evidence":
                    validated.get(
                        "evidence",
                        [],
                    ),
            }


        vmid = validated[
            "vmid"
        ]

        guest = validated[
            "guest"
        ]

        evidence = list(
            validated.get(
                "evidence",
                [],
            )
        )

        evidence.append(
            "current_state="
            + guest.status
        )


        if guest.status == "running":

            return {
                "status":
                    "FAILED",

                "result": (
                    "Proxmox LXC "
                    + str(vmid)
                    + " is already running"
                ),

                "evidence":
                    evidence,
            }


        if guest.status != "stopped":

            return {
                "status":
                    "FAILED",

                "result": (
                    "Proxmox LXC "
                    + str(vmid)
                    + " cannot be started "
                    "from state "
                    + guest.status
                ),

                "evidence":
                    evidence,
            }


        endpoint = (
            "/api2/json/nodes/"
            + guest.node
            + "/lxc/"
            + str(vmid)
            + "/status/start"
        )


        try:

            task = (
                self.proxmox
                ._post(
                    endpoint
                )
            )

        except Exception as exc:

            return {
                "status":
                    "FAILED",

                "result": (
                    "Proxmox LXC start "
                    "request failed: "
                    + str(exc)
                ),

                "evidence":
                    evidence,
            }


        if not task:

            return {
                "status":
                    "FAILED",

                "result":
                    (
                        "Proxmox LXC start "
                        "request returned no task"
                    ),

                "evidence":
                    evidence,
            }


        evidence.append(
            "Proxmox LXC start requested "
            "for VMID="
            + str(vmid)
        )

        evidence.append(
            "Proxmox task="
            + str(task)
        )


        try:

            task_status = (
                self._wait_for_task(
                    guest.node,
                    task,
                )
            )

        except Exception as exc:

            return {
                "status":
                    "FAILED",

                "result": (
                    "Proxmox task "
                    "verification failed: "
                    + str(exc)
                ),

                "evidence":
                    evidence,
            }


        if not task_status:

            return {
                "status":
                    "FAILED",

                "result":
                    (
                        "Proxmox task status "
                        "could not be retrieved"
                    ),

                "evidence":
                    evidence,
            }


        task_state = (
            task_status.get(
                "status"
            )
        )

        exit_status = (
            task_status.get(
                "exitstatus"
            )
        )

        evidence.append(
            "task_status="
            + str(task_state)
        )

        evidence.append(
            "task_exitstatus="
            + str(exit_status)
        )


        if (
            task_state != "stopped"
            or exit_status != "OK"
        ):

            return {
                "status":
                    "FAILED",

                "result": (
                    "Proxmox LXC start "
                    "task failed: status="
                    + str(task_state)
                    + ", exitstatus="
                    + str(exit_status)
                ),

                "evidence":
                    evidence,
            }


        try:

            final_state = (
                self._wait_for_state(
                    vmid,
                    "running",
                    guest_type="lxc",
                )
            )

        except Exception as exc:

            return {
                "status":
                    "FAILED",

                "result": (
                    "Proxmox LXC state "
                    "verification failed: "
                    + str(exc)
                ),

                "evidence":
                    evidence,
            }


        evidence.append(
            "verified_state="
            + str(final_state)
        )


        if final_state != "running":

            return {
                "status":
                    "FAILED",

                "result": (
                    "Proxmox LXC start "
                    "verification failed: state="
                    + str(final_state)
                ),

                "evidence":
                    evidence,
            }


        return {
            "status":
                "SUCCESS",

            "result": (
                "LXC "
                + str(vmid)
                + " running"
            ),

            "evidence":
                evidence,
        }


    def stop_lxc(
        self,
        target,
    ):

        validated = (
            self._validate_lxc_target(
                target
            )
        )

        if not validated[
            "ok"
        ]:

            return {
                "status": "FAILED",
                "result":
                    validated[
                        "result"
                    ],
                "evidence":
                    validated.get(
                        "evidence",
                        [],
                    ),
            }


        vmid = validated[
            "vmid"
        ]

        guest = validated[
            "guest"
        ]

        evidence = list(
            validated.get(
                "evidence",
                [],
            )
        )

        evidence.append(
            "current_state="
            + guest.status
        )


        if guest.status == "stopped":

            return {
                "status":
                    "FAILED",

                "result": (
                    "Proxmox LXC "
                    + str(vmid)
                    + " is already stopped"
                ),

                "evidence":
                    evidence,
            }


        if guest.status != "running":

            return {
                "status":
                    "FAILED",

                "result": (
                    "Proxmox LXC "
                    + str(vmid)
                    + " cannot be stopped "
                    "from state "
                    + guest.status
                ),

                "evidence":
                    evidence,
            }


        endpoint = (
            "/api2/json/nodes/"
            + guest.node
            + "/lxc/"
            + str(vmid)
            + "/status/stop"
        )


        try:

            task = (
                self.proxmox
                ._post(
                    endpoint
                )
            )

        except Exception as exc:

            return {
                "status":
                    "FAILED",

                "result": (
                    "Proxmox LXC stop "
                    "request failed: "
                    + str(exc)
                ),

                "evidence":
                    evidence,
            }


        if not task:

            return {
                "status":
                    "FAILED",

                "result":
                    (
                        "Proxmox LXC stop "
                        "request returned no task"
                    ),

                "evidence":
                    evidence,
            }


        evidence.append(
            "Proxmox LXC stop requested "
            "for VMID="
            + str(vmid)
        )

        evidence.append(
            "Proxmox task="
            + str(task)
        )


        try:

            task_status = (
                self._wait_for_task(
                    guest.node,
                    task,
                )
            )

        except Exception as exc:

            return {
                "status":
                    "FAILED",

                "result": (
                    "Proxmox task "
                    "verification failed: "
                    + str(exc)
                ),

                "evidence":
                    evidence,
            }


        if not task_status:

            return {
                "status":
                    "FAILED",

                "result":
                    (
                        "Proxmox task status "
                        "could not be retrieved"
                    ),

                "evidence":
                    evidence,
            }


        task_state = (
            task_status.get(
                "status"
            )
        )

        exit_status = (
            task_status.get(
                "exitstatus"
            )
        )

        evidence.append(
            "task_status="
            + str(task_state)
        )

        evidence.append(
            "task_exitstatus="
            + str(exit_status)
        )


        if (
            task_state != "stopped"
            or exit_status != "OK"
        ):

            return {
                "status":
                    "FAILED",

                "result": (
                    "Proxmox LXC stop "
                    "task failed: status="
                    + str(task_state)
                    + ", exitstatus="
                    + str(exit_status)
                ),

                "evidence":
                    evidence,
            }


        try:

            final_state = (
                self._wait_for_state(
                    vmid,
                    "stopped",
                    guest_type="lxc",
                )
            )

        except Exception as exc:

            return {
                "status":
                    "FAILED",

                "result": (
                    "Proxmox LXC state "
                    "verification failed: "
                    + str(exc)
                ),

                "evidence":
                    evidence,
            }


        evidence.append(
            "verified_state="
            + str(final_state)
        )


        if final_state != "stopped":

            return {
                "status":
                    "FAILED",

                "result": (
                    "Proxmox LXC stop "
                    "verification failed: state="
                    + str(final_state)
                ),

                "evidence":
                    evidence,
            }


        return {
            "status":
                "SUCCESS",

            "result": (
                "LXC "
                + str(vmid)
                + " stopped"
            ),

            "evidence":
                evidence,
        }


    def restart_lxc(
        self,
        target,
    ):

        validated = (
            self._validate_lxc_target(
                target
            )
        )

        if not validated[
            "ok"
        ]:

            return {
                "status": "FAILED",
                "result":
                    validated[
                        "result"
                    ],
                "evidence":
                    validated.get(
                        "evidence",
                        [],
                    ),
            }

        vmid = validated[
            "vmid"
        ]

        guest = validated[
            "guest"
        ]

        evidence = list(
            validated.get(
                "evidence",
                [],
            )
        )

        evidence.append(
            "current_state="
            + guest.status
        )

        if guest.status != "running":

            return {
                "status": "FAILED",
                "result": (
                    "Proxmox LXC "
                    + str(vmid)
                    + " is not running "
                    "(state="
                    + guest.status
                    + ")"
                ),
                "evidence": evidence,
            }

        endpoint = (
            "/api2/json/nodes/"
            + guest.node
            + "/lxc/"
            + str(vmid)
            + "/status/reboot"
        )

        try:

            task = (
                self.proxmox
                ._post(
                    endpoint
                )
            )

        except Exception as exc:

            return {
                "status": "FAILED",
                "result": (
                    "Proxmox LXC reboot "
                    "request failed: "
                    + str(exc)
                ),
                "evidence": evidence,
            }

        evidence.append(
            "Proxmox LXC reboot requested "
            "for VMID="
            + str(vmid)
        )

        if not task:

            return {
                "status": "FAILED",
                "result": (
                    "Proxmox LXC reboot "
                    "request returned no task"
                ),
                "evidence": evidence,
            }

        evidence.append(
            "Proxmox task="
            + str(task)
        )

        try:

            task_status = (
                self._wait_for_task(
                    guest.node,
                    task,
                )
            )

        except Exception as exc:

            return {
                "status": "FAILED",
                "result": (
                    "Proxmox task "
                    "verification failed: "
                    + str(exc)
                ),
                "evidence": evidence,
            }

        if not task_status:

            return {
                "status": "FAILED",
                "result": (
                    "Proxmox task status "
                    "could not be retrieved"
                ),
                "evidence": evidence,
            }

        task_state = (
            task_status.get(
                "status"
            )
        )

        exit_status = (
            task_status.get(
                "exitstatus"
            )
        )

        evidence.append(
            "task_status="
            + str(task_state)
        )

        evidence.append(
            "task_exitstatus="
            + str(exit_status)
        )

        if (
            task_state != "stopped"
            or exit_status != "OK"
        ):

            return {
                "status": "FAILED",
                "result": (
                    "Proxmox LXC reboot "
                    "task failed: status="
                    + str(task_state)
                    + ", exitstatus="
                    + str(exit_status)
                ),
                "evidence": evidence,
            }

        try:

            final_state = (
                self._wait_for_state(
                    vmid,
                    "running",
                    guest_type="lxc",
                )
            )

        except Exception as exc:

            return {
                "status": "FAILED",
                "result": (
                    "Proxmox LXC state "
                    "verification failed: "
                    + str(exc)
                ),
                "evidence": evidence,
            }

        evidence.append(
            "verified_state="
            + str(final_state)
        )

        if final_state != "running":

            return {
                "status": "FAILED",
                "result": (
                    "Proxmox LXC reboot "
                    "verification failed: state="
                    + str(final_state)
                ),
                "evidence": evidence,
            }

        evidence.append(
            "Proxmox LXC reboot verification passed"
        )

        return {
            "status": "SUCCESS",
            "result": (
                "LXC "
                + str(vmid)
                + " rebooted and running"
            ),
            "evidence": evidence,
        }
