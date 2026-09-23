from atlas.config.proxmox import (
    get_proxmox_config,
)


PROXMOX_ENV = (
    "ATLAS_PROXMOX_URL",
    "ATLAS_PROXMOX_TOKEN",
    "ATLAS_PROXMOX_HOST",
    "ATLAS_PROXMOX_VERIFY_SSL",
    "ATLAS_PROXMOX_CA_BUNDLE",
)


def clear_proxmox_env(
    monkeypatch,
):
    for key in PROXMOX_ENV:
        monkeypatch.delenv(
            key,
            raising=False,
        )


def test_proxmox_config_has_no_infrastructure_defaults(
    monkeypatch,
):

    clear_proxmox_env(
        monkeypatch
    )

    config = (
        get_proxmox_config()
    )

    assert config.url is None
    assert config.token is None
    assert config.host is None
    assert config.ca_bundle is None

    assert (
        config.verify_ssl
        is False
    )

    assert (
        config.requests_verify
        is False
    )


def test_boolean_ssl_verification(
    monkeypatch,
):

    clear_proxmox_env(
        monkeypatch
    )

    monkeypatch.setenv(
        "ATLAS_PROXMOX_VERIFY_SSL",
        "true",
    )

    config = (
        get_proxmox_config()
    )

    assert (
        config.verify_ssl
        is True
    )

    assert (
        config.requests_verify
        is True
    )


def test_ca_bundle_takes_precedence(
    monkeypatch,
):

    clear_proxmox_env(
        monkeypatch
    )

    monkeypatch.setenv(
        "ATLAS_PROXMOX_VERIFY_SSL",
        "false",
    )

    monkeypatch.setenv(
        "ATLAS_PROXMOX_CA_BUNDLE",
        "/example/proxmox-ca.pem",
    )

    config = (
        get_proxmox_config()
    )

    assert (
        config.ca_bundle
        == "/example/proxmox-ca.pem"
    )

    assert (
        config.requests_verify
        == "/example/proxmox-ca.pem"
    )


def test_proxmox_configuration_detection(
    monkeypatch,
):

    from atlas.config.proxmox import (
        is_proxmox_configured,
    )

    clear_proxmox_env(
        monkeypatch
    )

    assert (
        is_proxmox_configured()
        is False
    )

    monkeypatch.setenv(
        "ATLAS_PROXMOX_HOST",
        "pve.example.internal",
    )

    assert (
        is_proxmox_configured()
        is True
    )
