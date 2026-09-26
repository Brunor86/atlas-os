from atlas.services.intelligence.execution.service import (
    ActionExecutionService,
)


class FakeProxmoxHandler:

    calls = []

    def start_vm(
        self,
        target,
    ):

        self.__class__.calls.append(
            target
        )

        return {
            "status": "SUCCESS",
            "result": (
                "VM "
                + str(target)
                + " running"
            ),
            "evidence": [
                "fake Proxmox execution",
            ],
        }


    def stop_vm(
        self,
        target,
    ):

        self.__class__.calls.append(
            (
                "stop",
                target,
            )
        )

        return {
            "status": "SUCCESS",
            "result": (
                "VM "
                + str(target)
                + " stopped"
            ),
            "evidence": [
                "fake Proxmox stop execution",
            ],
        }


    def restart_vm(
        self,
        target,
    ):

        self.__class__.calls.append(
            (
                "restart",
                target,
            )
        )

        return {
            "status": "SUCCESS",
            "result": (
                "VM "
                + str(target)
                + " restarted"
            ),
            "evidence": [
                "fake Proxmox restart execution",
            ],
        }


    def start_lxc(
        self,
        target,
    ):

        self.__class__.calls.append(
            (
                "start_lxc",
                target,
            )
        )

        return {
            "status": "SUCCESS",
            "result": (
                "LXC "
                + str(target)
                + " running"
            ),
            "evidence": [
                "fake Proxmox LXC start execution",
            ],
        }


    def restart_lxc(
        self,
        target,
    ):

        self.__class__.calls.append(
            (
                "restart_lxc",
                target,
            )
        )

        return {
            "status": "SUCCESS",
            "result": (
                "LXC "
                + str(target)
                + " restarted"
            ),
            "evidence": [
                "fake Proxmox LXC restart execution",
            ],
        }


    def stop_lxc(
        self,
        target,
    ):

        self.__class__.calls.append(
            (
                "stop_lxc",
                target,
            )
        )

        return {
            "status": "SUCCESS",
            "result": (
                "LXC "
                + str(target)
                + " stopped"
            ),
            "evidence": [
                "fake Proxmox LXC stop execution",
            ],
        }


def approved(
    action,
    target,
):

    return {
        "id":
            "approval-proxmox-test",

        "incident_id":
            "incident-proxmox-test",

        "action":
            action,

        "target":
            target,

        "status":
            "APPROVED",
    }


def test_start_vm_dispatches_to_proxmox_handler(
    monkeypatch,
):

    from atlas.services.intelligence.execution import (
        service as execution_module,
    )

    FakeProxmoxHandler.calls = []

    monkeypatch.setattr(
        execution_module,
        "ProxmoxActionHandler",
        FakeProxmoxHandler,
    )

    executor = (
        ActionExecutionService()
    )

    result = executor.execute(
        approved(
            "start vm",
            "300",
        )
    )

    assert result.status == "SUCCESS"

    assert result.result == (
        "VM 300 running"
    )

    assert (
        FakeProxmoxHandler.calls
        == [
            "300",
        ]
    )


def test_restart_vm_dispatches_to_proxmox_handler(
    monkeypatch,
):

    from atlas.services.intelligence.execution import (
        service as execution_module,
    )

    FakeProxmoxHandler.calls = []

    monkeypatch.setattr(
        execution_module,
        "ProxmoxActionHandler",
        FakeProxmoxHandler,
    )

    executor = (
        ActionExecutionService()
    )

    result = executor.execute(
        approved(
            "restart vm",
            "300",
        )
    )

    assert result.status == "SUCCESS"

    assert result.result == (
        "VM 300 restarted"
    )

    assert (
        FakeProxmoxHandler.calls
        == [
            (
                "restart",
                "300",
            ),
        ]
    )


def test_restart_lxc_dispatches_to_proxmox_handler(
    monkeypatch,
):

    from atlas.services.intelligence.execution import (
        service as execution_module,
    )

    FakeProxmoxHandler.calls = []

    monkeypatch.setattr(
        execution_module,
        "ProxmoxActionHandler",
        FakeProxmoxHandler,
    )

    executor = (
        ActionExecutionService()
    )

    result = executor.execute(
        approved(
            "restart lxc",
            "103",
        )
    )

    assert result.status == "SUCCESS"

    assert result.result == (
        "LXC 103 restarted"
    )

    assert (
        FakeProxmoxHandler.calls
        == [
            (
                "restart_lxc",
                "103",
            ),
        ]
    )


def test_stop_vm_dispatches_to_proxmox_handler(
    monkeypatch,
):

    from atlas.services.intelligence.execution import (
        service as execution_module,
    )

    FakeProxmoxHandler.calls = []

    monkeypatch.setattr(
        execution_module,
        "ProxmoxActionHandler",
        FakeProxmoxHandler,
    )

    executor = (
        ActionExecutionService()
    )

    result = executor.execute(
        approved(
            "stop vm",
            "300",
        )
    )

    assert result.status == "SUCCESS"

    assert result.result == (
        "VM 300 stopped"
    )

    assert (
        FakeProxmoxHandler.calls
        == [
            (
                "stop",
                "300",
            ),
        ]
    )


def test_start_and_stop_lxc_dispatch_to_proxmox_handler(
    monkeypatch,
):

    from atlas.services.intelligence.execution import (
        service as execution_module,
    )

    FakeProxmoxHandler.calls = []

    monkeypatch.setattr(
        execution_module,
        "ProxmoxActionHandler",
        FakeProxmoxHandler,
    )

    executor = (
        ActionExecutionService()
    )


    start = executor.execute(
        approved(
            "start lxc",
            "103",
        )
    )

    assert start.status == "SUCCESS"

    assert start.result == (
        "LXC 103 running"
    )


    stop = executor.execute(
        approved(
            "stop lxc",
            "103",
        )
    )

    assert stop.status == "SUCCESS"

    assert stop.result == (
        "LXC 103 stopped"
    )


    assert (
        FakeProxmoxHandler.calls
        == [
            (
                "start_lxc",
                "103",
            ),
            (
                "stop_lxc",
                "103",
            ),
        ]
    )
