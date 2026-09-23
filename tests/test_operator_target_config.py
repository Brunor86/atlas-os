import pytest

from atlas.config.operator import (
    get_executable_systemd_services,
    get_executable_qemu_vmids,
    get_executable_lxc_vmids,
)


ENV_NAMES = (
    "ATLAS_OPERATOR_SYSTEMD_SERVICES",
    "ATLAS_OPERATOR_QEMU_VMIDS",
    "ATLAS_OPERATOR_LXC_VMIDS",
)


def clear_operator_target_env(
    monkeypatch,
):
    for name in ENV_NAMES:
        monkeypatch.delenv(
            name,
            raising=False,
        )


def test_operator_target_defaults_are_empty(
    monkeypatch,
):
    clear_operator_target_env(
        monkeypatch
    )

    assert (
        get_executable_systemd_services()
        == frozenset()
    )

    assert (
        get_executable_qemu_vmids()
        == frozenset()
    )

    assert (
        get_executable_lxc_vmids()
        == frozenset()
    )


def test_operator_target_allowlists_are_explicit(
    monkeypatch,
):
    clear_operator_target_env(
        monkeypatch
    )

    monkeypatch.setenv(
        "ATLAS_OPERATOR_SYSTEMD_SERVICES",
        "alpha.service,beta.service",
    )

    monkeypatch.setenv(
        "ATLAS_OPERATOR_QEMU_VMIDS",
        "120,300",
    )

    monkeypatch.setenv(
        "ATLAS_OPERATOR_LXC_VMIDS",
        "103,450",
    )

    assert (
        get_executable_systemd_services()
        == frozenset(
            {
                "alpha.service",
                "beta.service",
            }
        )
    )

    assert (
        get_executable_qemu_vmids()
        == frozenset(
            {
                120,
                300,
            }
        )
    )

    assert (
        get_executable_lxc_vmids()
        == frozenset(
            {
                103,
                450,
            }
        )
    )


def test_invalid_operator_vmid_config_fails_closed(
    monkeypatch,
):
    clear_operator_target_env(
        monkeypatch
    )

    monkeypatch.setenv(
        "ATLAS_OPERATOR_QEMU_VMIDS",
        "300,not-a-vmid",
    )

    with pytest.raises(
        RuntimeError
    ):
        get_executable_qemu_vmids()
