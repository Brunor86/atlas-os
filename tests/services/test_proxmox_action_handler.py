from types import SimpleNamespace

from atlas.services.intelligence.execution.handlers.proxmox import (
    ProxmoxActionHandler,
)
from atlas.services.intelligence.execution.validators import (
    ActionValidator,
)


class FakeProxmox:

    def __init__(
        self,
        *,
        status="stopped",
        conflicts=None,
    ):

        self.status = status

        self.conflicts = (
            conflicts
            or []
        )

        self.posts = []


    def resolve_guest(
        self,
        vmid,
        expected_type=None,
    ):

        assert expected_type == "qemu"

        current_status = (
            "running"
            if self.posts
            else self.status
        )

        return SimpleNamespace(
            vmid=int(
                vmid
            ),
            name="atlas-windows",
            type="qemu",
            node="atlas",
            status=current_status,
        )


    def running_qemu_pci_conflicts(
        self,
        vmid,
    ):

        assert int(
            vmid
        ) == 300

        return list(
            self.conflicts
        )


    def _post(
        self,
        endpoint,
        data=None,
    ):

        self.posts.append(
            {
                "endpoint":
                    endpoint,
                "data":
                    data,
            }
        )

        return (
            "UPID:atlas:"
            "00000001:"
            "start"
        )


def handler(
    fake,
):

    return ProxmoxActionHandler(
        proxmox=fake,
        poll_attempts=2,
        poll_interval=0,
        allowed_qemu_vmids={300},
        allowed_lxc_vmids={103},
    )


def test_non_allowlisted_vm_is_blocked():

    fake = FakeProxmox()

    result = (
        handler(
            fake
        )
        .start_vm(
            "200"
        )
    )

    assert result[
        "status"
    ] == "FAILED"

    assert (
        "not allowed"
        in result[
            "result"
        ]
    )

    assert fake.posts == []


def test_invalid_vmid_is_blocked():

    fake = FakeProxmox()

    result = (
        handler(
            fake
        )
        .start_vm(
            "atlas-windows"
        )
    )

    assert result[
        "status"
    ] == "FAILED"

    assert fake.posts == []


def test_running_vm_is_not_started():

    fake = FakeProxmox(
        status="running"
    )

    result = (
        handler(
            fake
        )
        .start_vm(
            "300"
        )
    )

    assert result[
        "status"
    ] == "FAILED"

    assert (
        "already running"
        in result[
            "result"
        ]
    )

    assert fake.posts == []


def test_pci_conflict_blocks_before_post():

    fake = FakeProxmox(
        conflicts=[
            {
                "vmid": 200,
                "name": "atlas-ai",
                "node": "atlas",
                "devices": [
                    "0000:01:00.0",
                    "0000:01:00.1",
                ],
            }
        ]
    )

    result = (
        handler(
            fake
        )
        .start_vm(
            "300"
        )
    )

    assert result[
        "status"
    ] == "FAILED"

    assert (
        "PCI conflict"
        in result[
            "result"
        ]
    )

    assert fake.posts == []

    assert any(
        (
            "VMID=200"
            in item
            and "atlas-ai"
            in item
        )
        for item
        in result[
            "evidence"
        ]
    )


def test_start_vm_posts_only_after_safety_checks():

    fake = FakeProxmox()

    result = (
        handler(
            fake
        )
        .start_vm(
            "300"
        )
    )

    assert result[
        "status"
    ] == "SUCCESS"

    assert fake.posts == [
        {
            "endpoint":
                (
                    "/api2/json/nodes/"
                    "atlas/qemu/300/"
                    "status/start"
                ),
            "data": None,
        }
    ]

    assert (
        "VM 300 running"
        == result[
            "result"
        ]
    )


def test_executor_allows_start_stop_and_restart_vm_pilot():

    assert (
        "start vm"
        in
        ActionValidator.ALLOWED_ACTIONS
    )

    assert (
        "restart vm"
        in
        ActionValidator.ALLOWED_ACTIONS
    )

    assert (
        "stop vm"
        in
        ActionValidator.ALLOWED_ACTIONS
    )

    assert (
        "start lxc"
        not in
        ActionValidator.ALLOWED_ACTIONS
    )

    assert (
        "restart lxc"
        in
        ActionValidator.ALLOWED_ACTIONS
    )

    assert (
        "stop lxc"
        not in
        ActionValidator.ALLOWED_ACTIONS
    )


# ATLAS v0.123 · STOP VM EXECUTION


class FakeStopProxmox(FakeProxmox):

    def __init__(
        self,
        *,
        status="running",
        transition=True,
        post_error=None,
    ):

        super().__init__(
            status=status
        )

        self.transition = transition
        self.post_error = post_error


    def resolve_guest(
        self,
        vmid,
        expected_type=None,
    ):

        assert expected_type == "qemu"

        current_status = self.status

        if (
            self.posts
            and self.transition
        ):
            current_status = "stopped"

        return SimpleNamespace(
            vmid=int(vmid),
            name="atlas-windows",
            type="qemu",
            node="atlas",
            status=current_status,
        )


    def _post(
        self,
        endpoint,
        data=None,
    ):

        if self.post_error:
            raise RuntimeError(
                self.post_error
            )

        self.posts.append(
            {
                "endpoint":
                    endpoint,
                "data":
                    data,
            }
        )

        return (
            "UPID:atlas:"
            "00000002:"
            "stop"
        )


def test_stop_vm_posts_and_verifies_stopped_state():

    fake = FakeStopProxmox(
        status="running"
    )

    result = (
        handler(fake)
        .stop_vm("300")
    )

    assert result["status"] == "SUCCESS"

    assert result["result"] == (
        "VM 300 stopped"
    )

    assert fake.posts == [
        {
            "endpoint":
                (
                    "/api2/json/nodes/"
                    "atlas/qemu/300/"
                    "status/stop"
                ),
            "data": None,
        }
    ]

    assert (
        "verified_state=stopped"
        in result["evidence"]
    )


def test_stop_vm_already_stopped_is_rejected_without_post():

    fake = FakeStopProxmox(
        status="stopped"
    )

    result = (
        handler(fake)
        .stop_vm("300")
    )

    assert result["status"] == "FAILED"

    assert (
        "already stopped"
        in result["result"]
    )

    assert fake.posts == []


def test_stop_vm_verification_failure_returns_failed():

    fake = FakeStopProxmox(
        status="running",
        transition=False,
    )

    result = (
        handler(fake)
        .stop_vm("300")
    )

    assert result["status"] == "FAILED"

    assert (
        "verification failed"
        in result["result"]
    )

    assert len(fake.posts) == 1


def test_stop_vm_request_failure_returns_failed():

    fake = FakeStopProxmox(
        status="running",
        post_error="synthetic stop failure",
    )

    result = (
        handler(fake)
        .stop_vm("300")
    )

    assert result["status"] == "FAILED"

    assert (
        "synthetic stop failure"
        in result["result"]
    )


def test_stop_vm_non_allowlisted_target_never_posts():

    fake = FakeStopProxmox(
        status="running"
    )

    result = (
        handler(fake)
        .stop_vm("200")
    )

    assert result["status"] == "FAILED"

    assert fake.posts == []


# ATLAS v0.124 · RESTART VM EXECUTION


def test_restart_vm_sequences_stop_then_start(
    monkeypatch,
):

    fake = FakeStopProxmox(
        status="running"
    )

    instance = handler(fake)

    calls = []

    def fake_stop(target):

        calls.append(
            (
                "stop",
                target,
            )
        )

        return {
            "status": "SUCCESS",
            "result": "VM 300 stopped",
            "evidence": [
                "stop evidence",
            ],
        }

    def fake_start(target):

        calls.append(
            (
                "start",
                target,
            )
        )

        return {
            "status": "SUCCESS",
            "result": "VM 300 running",
            "evidence": [
                "start evidence",
            ],
        }

    monkeypatch.setattr(
        instance,
        "stop_vm",
        fake_stop,
    )

    monkeypatch.setattr(
        instance,
        "start_vm",
        fake_start,
    )

    result = instance.restart_vm(
        "300"
    )

    assert result["status"] == "SUCCESS"

    assert calls == [
        (
            "stop",
            "300",
        ),
        (
            "start",
            "300",
        ),
    ]

    assert (
        "stop evidence"
        in result["evidence"]
    )

    assert (
        "start evidence"
        in result["evidence"]
    )


def test_restart_vm_stop_failure_short_circuits_start(
    monkeypatch,
):

    fake = FakeStopProxmox(
        status="running"
    )

    instance = handler(fake)

    calls = []

    def fake_stop(target):

        calls.append(
            "stop"
        )

        return {
            "status": "FAILED",
            "result": "synthetic stop failure",
            "evidence": [
                "stop failed",
            ],
        }

    def fake_start(target):

        calls.append(
            "start"
        )

        raise AssertionError(
            "start must not run"
        )

    monkeypatch.setattr(
        instance,
        "stop_vm",
        fake_stop,
    )

    monkeypatch.setattr(
        instance,
        "start_vm",
        fake_start,
    )

    result = instance.restart_vm(
        "300"
    )

    assert result["status"] == "FAILED"

    assert calls == [
        "stop",
    ]

    assert (
        "stop failed"
        in result["evidence"]
    )


def test_restart_vm_start_failure_is_preserved(
    monkeypatch,
):

    fake = FakeStopProxmox(
        status="running"
    )

    instance = handler(fake)

    calls = []

    def fake_stop(target):

        calls.append(
            "stop"
        )

        return {
            "status": "SUCCESS",
            "result": "VM 300 stopped",
            "evidence": [
                "stop complete",
            ],
        }

    def fake_start(target):

        calls.append(
            "start"
        )

        return {
            "status": "FAILED",
            "result": "PCI conflict blocks start",
            "evidence": [
                "PCI conflict",
            ],
        }

    monkeypatch.setattr(
        instance,
        "stop_vm",
        fake_stop,
    )

    monkeypatch.setattr(
        instance,
        "start_vm",
        fake_start,
    )

    result = instance.restart_vm(
        "300"
    )

    assert result["status"] == "FAILED"

    assert calls == [
        "stop",
        "start",
    ]

    assert (
        "stop complete"
        in result["evidence"]
    )

    assert (
        "PCI conflict"
        in result["evidence"]
    )


# ATLAS v0.127 · CONTROLLED LXC RESTART EXECUTION

class FakeLxcRestartProxmox:
    def __init__(
        self,
        *,
        status="stopped",
        poll_results=None,
        post_error=None,
    ):
        self.status = status
        self.posts = []
        self.gets = []
        self.expected_types = []
        self.poll_results = list(poll_results or [])
        self.post_error = post_error

    def resolve_guest(self, vmid, expected_type):
        self.expected_types.append(expected_type)
        return SimpleNamespace(
            vmid=int(vmid),
            node="atlas",
            type=expected_type,
            status=self.status,
            name=f"lxc-{vmid}",
        )

    def _post(self, endpoint, data=None):
        if self.post_error:
            raise self.post_error
        self.posts.append(endpoint)
        return "UPID:atlas:00000001:reboot"

    def _get(self, endpoint):
        self.gets.append(endpoint)
        if self.poll_results:
            return self.poll_results.pop(0)
        return {"status": "running"}


def lxc_handler(fake):
    return ProxmoxActionHandler(
        proxmox=fake,
        poll_attempts=3,
        poll_interval=0,
        allowed_qemu_vmids={300},
        allowed_lxc_vmids={103},
    )


def test_restart_lxc_reboots_allowlisted_guest_and_verifies_task():
    fake = FakeLxcRestartProxmox(
        status="running",
        poll_results=[
            {"status": "running"},
            {"status": "stopped", "exitstatus": "OK"},
        ],
    )
    result = lxc_handler(fake).restart_lxc("103")
    assert result["status"] == "SUCCESS"
    assert fake.posts[0] == "/api2/json/nodes/atlas/lxc/103/status/reboot"
    assert len(fake.gets) > 0
    assert any("/tasks/" in g for g in fake.gets)
    assert any(g.endswith("/status") for g in fake.gets)
    assert any("%3A" in endpoint for endpoint in fake.gets)
    assert fake.expected_types, "expected_types should not be empty"
    assert all(t == "lxc" for t in fake.expected_types)
    assert "verified_state=running" in result["evidence"]


def test_restart_lxc_non_allowlisted_target_never_posts():
    fake = FakeLxcRestartProxmox(status="running")
    result = lxc_handler(fake).restart_lxc("102")
    assert result["status"] == "FAILED"
    assert not fake.posts
    assert not fake.gets


def test_restart_lxc_requires_running_guest():
    fake = FakeLxcRestartProxmox(status="stopped")
    result = lxc_handler(fake).restart_lxc("103")
    assert result["status"] == "FAILED"
    assert not fake.posts
    assert not fake.gets


def test_restart_lxc_post_failure_returns_failed():
    fake = FakeLxcRestartProxmox(
        status="running",
        post_error=RuntimeError("synthetic reboot failure"),
    )
    result = lxc_handler(fake).restart_lxc("103")
    assert result["status"] == "FAILED"
    assert not fake.posts
    assert not fake.gets


def test_restart_lxc_failed_task_never_reports_success():
    fake = FakeLxcRestartProxmox(
        status="running",
        poll_results=[
            {"status": "stopped", "exitstatus": "ERROR"},
        ],
    )
    result = lxc_handler(fake).restart_lxc("103")
    assert result["status"] == "FAILED"
    assert len(fake.posts) == 1
    assert len(fake.gets) == 1


def test_restart_lxc_task_timeout_never_reports_success():
    fake = FakeLxcRestartProxmox(
        status="running",
        poll_results=[
            {"status": "running"},
            {"status": "running"},
            {"status": "running"},
        ],
    )
    result = lxc_handler(fake).restart_lxc("103")
    assert result["status"] == "FAILED"
    assert len(fake.posts) == 1
    assert len(fake.gets) == 3
