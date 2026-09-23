import re
import runpy
from pathlib import Path

import pytest

from atlas.config.ai import (
    DEFAULT_OLLAMA_HOST,
    DEFAULT_OLLAMA_PORT,
    get_ollama_config,
)


ROOT = Path(__file__).resolve().parents[1]


def _boot_probe():

    return runpy.run_path(
        str(
            ROOT
            / "ops"
            / "bin"
            / "atlas-wait-ready"
        )
    )


def test_ollama_defaults_are_local(
    monkeypatch,
):

    monkeypatch.delenv(
        "ATLAS_OLLAMA_HOST",
        raising=False,
    )

    monkeypatch.delenv(
        "ATLAS_OLLAMA_PORT",
        raising=False,
    )

    config = get_ollama_config()

    assert (
        config.host
        == DEFAULT_OLLAMA_HOST
        == "127.0.0.1"
    )

    assert (
        config.port
        == DEFAULT_OLLAMA_PORT
        == 11434
    )


def test_ollama_endpoint_is_configurable(
    monkeypatch,
):

    monkeypatch.setenv(
        "ATLAS_OLLAMA_HOST",
        "ai.example.internal",
    )

    monkeypatch.setenv(
        "ATLAS_OLLAMA_PORT",
        "12434",
    )

    config = get_ollama_config()

    assert (
        config.host
        == "ai.example.internal"
    )

    assert (
        config.port
        == 12434
    )


def test_invalid_ollama_port_fails_closed(
    monkeypatch,
):

    monkeypatch.setenv(
        "ATLAS_OLLAMA_PORT",
        "invalid",
    )

    with pytest.raises(
        RuntimeError,
        match="must be an integer",
    ):
        get_ollama_config()


def test_boot_probe_skips_unconfigured_proxmox(
    monkeypatch,
):

    monkeypatch.delenv(
        "ATLAS_PROXMOX_URL",
        raising=False,
    )

    module = _boot_probe()

    assert (
        module[
            "proxmox_target"
        ]()
        is None
    )

    ok, detail = module[
        "proxmox_ready"
    ]()

    assert ok is True
    assert detail == "not configured"


def test_boot_probe_parses_configured_proxmox(
    monkeypatch,
):

    monkeypatch.setenv(
        "ATLAS_PROXMOX_URL",
        "https://proxmox.example.internal:8006",
    )

    module = _boot_probe()

    assert (
        module[
            "proxmox_target"
        ]()
        == (
            "https://proxmox.example.internal:8006",
            "proxmox.example.internal",
            8006,
        )
    )


def test_active_public_source_has_no_private_ipv4_defaults():

    private_ipv4 = re.compile(
        r"""
        (?:
            10\.
            |
            192\.168\.
            |
            172\.
            (?:
                1[6-9]
                |
                2[0-9]
                |
                3[01]
            )
            \.
        )
        \d{1,3}
        \.
        \d{1,3}
        """,
        re.VERBOSE,
    )

    offenders = []

    for root_name in (
        "src",
        "ops",
        "scripts",
    ):

        root = (
            ROOT
            / root_name
        )

        for path in root.rglob(
            "*"
        ):

            if not path.is_file():
                continue

            if ".bak" in path.name:
                continue

            try:
                text = path.read_text(
                    encoding="utf-8",
                )

            except UnicodeDecodeError:
                continue

            if private_ipv4.search(
                text
            ):
                offenders.append(
                    str(
                        path.relative_to(
                            ROOT
                        )
                    )
                )

    assert offenders == []


def test_legacy_settings_module_is_removed():

    assert not (
        ROOT
        / "src"
        / "atlas"
        / "settings.py"
    ).exists()


def test_boot_installer_uses_standard_backup_root():

    text = (
        ROOT
        / "scripts"
        / "install-boot-hardening.sh"
    ).read_text(
        encoding="utf-8",
    )

    assert (
        "/var/backups/atlas"
        in text
    )

    assert (
        "/opt/atlas-backups"
        not in text
    )


def test_boot_probe_skips_absent_docker(
    monkeypatch,
):

    module = _boot_probe()

    monkeypatch.setattr(
        module["shutil"],
        "which",
        lambda name:
            None,
    )

    monkeypatch.setattr(
        module["os"].path,
        "exists",
        lambda path:
            False,
    )

    ok, detail = module[
        "docker_ready"
    ]()

    assert ok is True
    assert detail == "not configured"


def test_boot_probe_waits_when_docker_cli_exists_without_socket(
    monkeypatch,
):

    module = _boot_probe()

    monkeypatch.setattr(
        module["shutil"],
        "which",
        lambda name:
            "/usr/bin/docker",
    )

    monkeypatch.setattr(
        module["os"].path,
        "exists",
        lambda path:
            False,
    )

    ok, detail = module[
        "docker_ready"
    ]()

    assert ok is False
    assert (
        detail
        == "docker socket not present"
    )


def test_boot_probe_waits_when_socket_exists_without_cli(
    monkeypatch,
):

    module = _boot_probe()

    monkeypatch.setattr(
        module["shutil"],
        "which",
        lambda name:
            None,
    )

    monkeypatch.setattr(
        module["os"].path,
        "exists",
        lambda path:
            path == "/var/run/docker.sock",
    )

    ok, detail = module[
        "docker_ready"
    ]()

    assert ok is False
    assert (
        detail
        == "docker executable not found"
    )
