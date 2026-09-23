from hashlib import sha256
from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

WAIT_READY = (
    ROOT
    / "ops"
    / "bin"
    / "atlas-wait-ready"
)

DROPIN = (
    ROOT
    / "ops"
    / "systemd"
    / "atlas-collector.service.d"
    / "boot-hardening.conf"
)


WAIT_READY_SHA256 = (
    "ca46869196a9b0ec578cd911754d7d6a"
    "2b5f5f323e238472a314e588c9a1e9ca"
)

DROPIN_SHA256 = (
    "df1763c9def4a8d601e88d7a77c07de4"
    "0eb0080cd815e4f54f15638bfd0ee0e9"
)


def digest(path: Path) -> str:

    return sha256(
        path.read_bytes()
    ).hexdigest()


def test_validated_assets_are_present():

    assert WAIT_READY.is_file()
    assert DROPIN.is_file()


def test_wait_ready_matches_validated_live_asset():

    assert (
        digest(WAIT_READY)
        == WAIT_READY_SHA256
    )


def test_dropin_matches_validated_live_asset():

    assert (
        digest(DROPIN)
        == DROPIN_SHA256
    )


def test_wait_ready_python_syntax():

    source = WAIT_READY.read_text()

    compile(
        source,
        str(WAIT_READY),
        "exec",
    )


def test_wait_ready_contract():

    source = WAIT_READY.read_text()

    assert "TIMEOUT_SECONDS = 120" in source
    assert "INTERVAL_SECONDS = 3" in source

    assert (
        'ATLAS_PROXMOX_URL'
        in source
    )

    assert (
        '"not configured"'
        in source
    )

    assert (
        "192.168."
        not in source
    )

    assert (
        "docker info"
        not in source
    )

    assert (
        '"info",' in source
    )

    assert (
        "socket.create_connection"
        in source
    )

    assert (
        "time.sleep("
        in source
    )

    assert (
        "ATLAS boot readiness PASS"
        in source
    )

    assert (
        "ATLAS boot readiness FAILED"
        in source
    )


def test_systemd_dropin_contract():

    content = DROPIN.read_text()

    assert (
        "After=network-online.target"
        in content
    )

    assert (
        "Wants=network-online.target"
        in content
    )

    assert (
        "docker.service"
        not in content
    )

    assert (
        "ExecStartPre=/usr/local/sbin/atlas-wait-ready"
        in content
    )

    assert (
        "TimeoutStartSec=150"
        in content
    )

    assert "Requires=docker.service" not in content
