from pathlib import Path
import subprocess


ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)


INSTALLER = (
    ROOT
    / "scripts"
    / "install-atlas.sh"
)


COLLECTOR = (
    ROOT
    / "ops"
    / "systemd"
    / "atlas-collector.service"
)


WEB = (
    ROOT
    / "ops"
    / "systemd"
    / "atlas-web.service"
)


DROPIN = (
    ROOT
    / "ops"
    / "systemd"
    / "atlas-collector.service.d"
    / "boot-hardening.conf"
)


RUNTIME_EXAMPLE = (
    ROOT
    / "ops"
    / "config"
    / "atlas.env.example"
)


WEB_EXAMPLE = (
    ROOT
    / "ops"
    / "config"
    / "atlas-web.env.example"
)


def test_public_installer_assets_exist():

    for path in (
        INSTALLER,
        COLLECTOR,
        WEB,
        DROPIN,
        RUNTIME_EXAMPLE,
        WEB_EXAMPLE,
    ):

        assert path.is_file()


def test_public_installer_shell_syntax():

    subprocess.run(
        [
            "bash",
            "-n",
            str(
                INSTALLER
            ),
        ],
        check=True,
    )


def test_public_installer_uses_standard_layout():

    source = INSTALLER.read_text()

    assert (
        'PREFIX="/opt/atlas"'
        in source
    )

    assert (
        'CONFIG_DIR="/etc/atlas"'
        in source
    )

    assert (
        'STATE_DIR="/var/lib/atlas"'
        in source
    )

    assert (
        'BACKUP_ROOT="/var/backups/atlas"'
        in source
    )


def test_public_installer_installs_wheel_without_git():

    source = INSTALLER.read_text()

    assert (
        "--wheel"
        in source
    )

    assert (
        '"$WHEEL"'
        in source
    )

    assert (
        "git clone"
        not in source
    )

    assert (
        "git pull"
        not in source
    )


def test_public_runtime_defaults_to_standard_state_path():

    source = RUNTIME_EXAMPLE.read_text()

    assert (
        "ATLAS_DB_PATH=/var/lib/atlas/atlas.db"
        in source
    )


def test_public_web_defaults_to_loopback():

    source = RUNTIME_EXAMPLE.read_text()

    assert (
        "ATLAS_WEB_HOST=127.0.0.1"
        in source
    )

    assert (
        "ATLAS_WEB_PORT=8091"
        in source
    )

    assert (
        "ATLAS_WEB_HOST=0.0.0.0"
        not in source
    )


def test_public_operator_defaults_fail_closed():

    source = WEB_EXAMPLE.read_text()

    assert (
        "ATLAS_OPERATOR_SYSTEMD_SERVICES="
        in source
    )

    assert (
        "ATLAS_OPERATOR_QEMU_VMIDS="
        in source
    )

    assert (
        "ATLAS_OPERATOR_LXC_VMIDS="
        in source
    )


def test_public_installer_generates_operator_token():

    source = INSTALLER.read_text()

    assert (
        "secrets.token_urlsafe"
        in source
    )

    assert (
        "ATLAS_OPERATOR_TOKEN="
        in source
    )

    assert (
        "token   : <SET"
        in source
    )


def test_public_collector_unit_uses_wheel_runtime():

    source = COLLECTOR.read_text()

    assert (
        "WorkingDirectory=/var/lib/atlas"
        in source
    )

    assert (
        "EnvironmentFile=/etc/atlas/atlas.env"
        in source
    )

    assert (
        "ExecStart=/opt/atlas/venv/bin/python "
        "-m atlas.services.collector.worker"
        in source
    )


def test_public_web_unit_uses_wheel_runtime():

    source = WEB.read_text()

    assert (
        "WorkingDirectory=/var/lib/atlas"
        in source
    )

    assert (
        "EnvironmentFile=/etc/atlas/atlas.env"
        in source
    )

    assert (
        "EnvironmentFile=/etc/atlas/atlas-web.env"
        in source
    )

    assert (
        "/opt/atlas/venv/bin/python -m uvicorn"
        in source
    )

    assert (
        "${ATLAS_WEB_HOST}"
        in source
    )

    assert (
        "${ATLAS_WEB_PORT}"
        in source
    )


def test_public_systemd_has_no_docker_dependency():

    collector = COLLECTOR.read_text()
    dropin = DROPIN.read_text()

    assert (
        "docker.service"
        not in collector
    )

    assert (
        "docker.service"
        not in dropin
    )

    assert (
        "network-online.target"
        in collector
    )

    assert (
        "network-online.target"
        in dropin
    )


def test_public_installer_preserves_config_and_initializes_state():

    source = INSTALLER.read_text()

    assert (
        'if [ ! -f "$ATLAS_ENV" ]; then'
        in source
    )

    assert (
        'if [ ! -f "$ATLAS_WEB_ENV" ]; then'
        in source
    )

    assert (
        "SQLite quick_check: ok"
        in source
    )

    assert (
        "systemctl"
        in source
    )

    assert (
        "enable"
        in source
    )

    assert (
        "atlas-collector.service"
        in source
    )

    assert (
        "atlas-web.service"
        in source
    )


def test_public_installer_requires_absolute_database_path():

    source = INSTALLER.read_text()

    assert (
        'case "$DB_PATH" in'
        in source
    )

    assert (
        'ATLAS_DB_PATH must be an absolute path'
        in source
    )


def test_public_installer_validates_web_port():

    source = INSTALLER.read_text()

    assert (
        'ATLAS_WEB_PORT must be an integer between 1 and 65535'
        in source
    )

    assert (
        "1"
        "\n    <= port"
        "\n    <= 65535"
        in source
    )


def test_public_installer_health_probe_follows_web_bind():

    source = INSTALLER.read_text()

    assert (
        "ATLAS_WEB_HOST"
        in source
    )

    assert (
        'HEALTH_HOST="$WEB_HOST"'
        in source
    )

    assert (
        '0.0.0.0|::|"[::]"'
        in source
    )

    assert (
        'HEALTH_HOST="127.0.0.1"'
        in source
    )

    assert (
        '"$HEALTH_HOST"'
        in source
    )

    assert (
        "sys.argv[1]"
        in source
    )

    assert (
        "sys.argv[2]"
        in source
    )
