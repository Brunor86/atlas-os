import os


def _csv_values(
    name: str,
) -> tuple[str, ...]:
    """
    Read a comma-separated allowlist from the environment.

    Missing or empty configuration intentionally means that
    nothing is executable.
    """

    raw = str(
        os.getenv(
            name,
            "",
        )
        or ""
    ).strip()

    if not raw:
        return ()

    return tuple(
        item
        for item in (
            value.strip()
            for value in raw.split(",")
        )
        if item
    )


def get_executable_systemd_services() -> frozenset[str]:
    """
    Explicit systemd execution allowlist.

    Public/default behavior is fail-closed: no configured
    services means no systemd service can be mutated.
    """

    return frozenset(
        _csv_values(
            "ATLAS_OPERATOR_SYSTEMD_SERVICES"
        )
    )


def _vmid_allowlist(
    name: str,
) -> frozenset[int]:
    values = set()

    for raw in _csv_values(
        name
    ):

        try:
            vmid = int(
                raw
            )

        except ValueError as exc:
            raise RuntimeError(
                f"{name} contains invalid VMID: {raw}"
            ) from exc

        if vmid <= 0:
            raise RuntimeError(
                f"{name} contains invalid VMID: {raw}"
            )

        values.add(
            vmid
        )

    return frozenset(
        values
    )


def get_executable_qemu_vmids() -> frozenset[int]:
    """
    Explicit QEMU execution allowlist.

    Empty by default.
    """

    return _vmid_allowlist(
        "ATLAS_OPERATOR_QEMU_VMIDS"
    )


def get_executable_lxc_vmids() -> frozenset[int]:
    """
    Explicit LXC execution allowlist.

    Empty by default.
    """

    return _vmid_allowlist(
        "ATLAS_OPERATOR_LXC_VMIDS"
    )
