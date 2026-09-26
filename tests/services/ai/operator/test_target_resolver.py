from types import SimpleNamespace

from atlas.services.ai.operator.target_resolver import (
    OperationTargetResolver,
)


def asset(
    *,
    asset_id,
    name,
    asset_type,
    serial,
    model,
    vendor,
    presence="ACTIVE",
    metadata=None,
):
    return SimpleNamespace(
        id=asset_id,
        name=name,
        type=SimpleNamespace(
            name=asset_type
        ),
        presence=SimpleNamespace(
            name=presence
        ),
        identity=SimpleNamespace(
            serial=serial,
            model=model,
            vendor=vendor,
        ),
        metadata=metadata or {},
    )


class FakeRepository:

    def __init__(
        self,
        assets,
    ):
        self.assets = list(
            assets
        )

    def get_all_assets(
        self,
    ):
        return list(
            self.assets
        )


def resolver(
    *assets,
):
    return OperationTargetResolver(
        repository=FakeRepository(
            assets
        )
    )


def test_resolves_olivasat_name_to_lxc_vmid():

    result = resolver(
        asset(
            asset_id="lxc-103",
            name="olivasat",
            asset_type="LXC",
            serial="103",
            model="Linux Container",
            vendor="Proxmox",
            metadata={
                "proxmox_vmid": "103",
            },
        )
    ).resolve(
        "OlivaSat"
    )

    assert result.status == "RESOLVED"
    assert result.resource_type == "lxc"
    assert result.target == "103"
    assert result.asset_name == "olivasat"


def test_resolves_db_aceite_name_without_hardcoded_alias():

    result = resolver(
        asset(
            asset_id="lxc-102",
            name="DB-Aceite",
            asset_type="LXC",
            serial="102",
            model="Linux Container",
            vendor="Proxmox",
        )
    ).resolve(
        "db-aceite"
    )

    assert result.status == "RESOLVED"
    assert result.resource_type == "lxc"
    assert result.target == "102"


def test_resolves_vm_name_to_vmid():

    result = resolver(
        asset(
            asset_id="vm-200",
            name="atlas-ai",
            asset_type="VM",
            serial="200",
            model="Virtual Machine",
            vendor="Proxmox",
        )
    ).resolve(
        "ATLAS-AI"
    )

    assert result.status == "RESOLVED"
    assert result.resource_type == "vm"
    assert result.target == "200"


def test_resolves_numeric_vmid():

    result = resolver(
        asset(
            asset_id="vm-300",
            name="atlas-windows",
            asset_type="VM",
            serial="300",
            model="Virtual Machine",
            vendor="Proxmox",
        )
    ).resolve(
        "300",
        requested_resource_type="vm",
    )

    assert result.status == "RESOLVED"
    assert result.resource_type == "vm"
    assert result.target == "300"


def test_resolves_docker_container():

    result = resolver(
        asset(
            asset_id="docker-flaresolverr",
            name="flaresolverr",
            asset_type="APPLICATION",
            serial="flaresolverr",
            model="",
            vendor="Docker",
        )
    ).resolve(
        "flaresolverr"
    )

    assert result.status == "RESOLVED"
    assert result.resource_type == "container"
    assert result.target == "flaresolverr"


def test_resolves_systemd_service_without_suffix():

    result = resolver(
        asset(
            asset_id="service-atlas-collector",
            name="atlas-collector.service",
            asset_type="SERVICE",
            serial=(
                "debian-docker:"
                "atlas-collector.service"
            ),
            model="Systemd Service",
            vendor="Linux",
        )
    ).resolve(
        "atlas-collector"
    )

    assert result.status == "RESOLVED"
    assert result.resource_type == "service"
    assert result.target == "atlas-collector.service"


def test_retired_asset_is_not_resolved():

    result = resolver(
        asset(
            asset_id="retired-vm",
            name="old-vm",
            asset_type="VM",
            serial="999",
            model="Virtual Machine",
            vendor="Proxmox",
            presence="RETIRED",
        )
    ).resolve(
        "old-vm"
    )

    assert result.status == "NOT_FOUND"


def test_ambiguous_service_fails_closed():

    result = resolver(
        asset(
            asset_id="ssh-db",
            name="ssh.service",
            asset_type="SERVICE",
            serial="DB-Aceite:ssh.service",
            model="Systemd Service",
            vendor="Linux",
        ),
        asset(
            asset_id="ssh-olivasat",
            name="ssh.service",
            asset_type="SERVICE",
            serial="olivasat:ssh.service",
            model="Systemd Service",
            vendor="Linux",
        ),
    ).resolve(
        "ssh"
    )

    assert result.status == "AMBIGUOUS"
    assert len(
        result.candidates
    ) == 2


def test_explicit_wrong_resource_type_fails_closed():

    result = resolver(
        asset(
            asset_id="lxc-103",
            name="olivasat",
            asset_type="LXC",
            serial="103",
            model="Linux Container",
            vendor="Proxmox",
        )
    ).resolve(
        "olivasat",
        requested_resource_type="vm",
    )

    assert result.status == "TYPE_MISMATCH"


def test_unknown_target_fails_closed():

    result = resolver().resolve(
        "does-not-exist"
    )

    assert result.status == "NOT_FOUND"



def test_canonical_asset_name_outranks_derived_service_alias():

    result = resolver(
        asset(
            asset_id="lxc-103",
            name="olivasat",
            asset_type="LXC",
            serial="103",
            model="Linux Container",
            vendor="Proxmox",
        ),
        asset(
            asset_id="service-olivasat",
            name="olivasat.service",
            asset_type="SERVICE",
            serial="olivasat:olivasat.service",
            model="Systemd Service",
            vendor="Linux",
        ),
    ).resolve(
        "olivasat"
    )

    assert result.status == "RESOLVED"
    assert result.resource_type == "lxc"
    assert result.target == "103"
    assert result.asset_name == "olivasat"


def test_explicit_service_type_can_use_derived_service_alias():

    result = resolver(
        asset(
            asset_id="lxc-103",
            name="olivasat",
            asset_type="LXC",
            serial="103",
            model="Linux Container",
            vendor="Proxmox",
        ),
        asset(
            asset_id="service-olivasat",
            name="olivasat.service",
            asset_type="SERVICE",
            serial="olivasat:olivasat.service",
            model="Systemd Service",
            vendor="Linux",
        ),
    ).resolve(
        "olivasat",
        requested_resource_type="service",
    )

    assert result.status == "RESOLVED"
    assert result.resource_type == "service"
    assert result.target == "olivasat.service"
