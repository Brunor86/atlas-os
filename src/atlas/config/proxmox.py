import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ProxmoxConfig:

    url: str | None

    token: str | None

    host: str | None

    verify_ssl: bool

    ca_bundle: str | None

    @property
    def requests_verify(
        self,
    ) -> bool | str:
        """
        Value suitable for requests' verify= parameter.

        A configured CA bundle implies certificate verification and takes
        precedence over the boolean SSL verification flag.
        """

        if self.ca_bundle:
            return self.ca_bundle

        return self.verify_ssl


def get_proxmox_config() -> ProxmoxConfig:
    """
    Load Proxmox integration settings from the runtime environment.

    ATLAS deliberately provides no infrastructure-specific defaults.
    """

    url = (
        os.getenv(
            "ATLAS_PROXMOX_URL"
        )
        or None
    )

    token = (
        os.getenv(
            "ATLAS_PROXMOX_TOKEN"
        )
        or None
    )

    host = (
        os.getenv(
            "ATLAS_PROXMOX_HOST"
        )
        or None
    )

    ca_bundle = (
        os.getenv(
            "ATLAS_PROXMOX_CA_BUNDLE"
        )
        or None
    )

    verify_ssl = (
        os.getenv(
            "ATLAS_PROXMOX_VERIFY_SSL",
            "false",
        )
        .strip()
        .lower()
        in {
            "1",
            "true",
            "yes",
            "on",
        }
    )

    return ProxmoxConfig(
        url=url,
        token=token,
        host=host,
        verify_ssl=verify_ssl,
        ca_bundle=ca_bundle,
    )


def is_proxmox_configured() -> bool:
    # A completely absent optional provider must be skipped.
    # Partial configuration still counts as configured so
    # missing fields or connectivity failures remain visible.
    config = get_proxmox_config()

    return any(
        (
            config.url,
            config.token,
            config.host,
            config.ca_bundle,
        )
    )


def require_proxmox_api() -> ProxmoxConfig:
    """
    Return configured Proxmox API settings or fail explicitly.
    """

    config = get_proxmox_config()

    missing = []

    if not config.url:
        missing.append(
            "ATLAS_PROXMOX_URL"
        )

    if not config.token:
        missing.append(
            "ATLAS_PROXMOX_TOKEN"
        )

    if missing:
        raise RuntimeError(
            "Proxmox API is not configured; missing: "
            + ", ".join(missing)
        )

    return config


def require_proxmox_host() -> str:
    """
    Return configured Proxmox SSH endpoint or fail explicitly.
    """

    config = get_proxmox_config()

    if not config.host:
        raise RuntimeError(
            "Proxmox SSH is not configured; "
            "missing ATLAS_PROXMOX_HOST"
        )

    return config.host
