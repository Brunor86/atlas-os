from atlas.core.asset import (
    Asset,
    AssetType,
    AssetRole,
    ServiceRole,
)

from atlas.core.identity import AssetIdentity

from atlas.services.assets.role_inference import (
    RoleInferenceService,
)


def create_asset(
    name,
    asset_type,
):

    return Asset(

        id=name,

        name=name,

        type=asset_type,

        identity=AssetIdentity(),

    )



def test_service_role_inference():

    docker = create_asset(
        "docker.service",
        AssetType.SERVICE,
    )

    docker.metadata["hostname"] = "debian-docker"

    ssh = create_asset(
        "ssh.service",
        AssetType.SERVICE,
    )

    smart = create_asset(
        "smartmontools.service",
        AssetType.SERVICE,
    )


    assets = [
        docker,
        ssh,
        smart,
    ]


    RoleInferenceService().infer(
        assets
    )


    assert (
        docker.service_role
        == ServiceRole.CONTAINER_RUNTIME
    )


    assert (
        ssh.service_role
        == ServiceRole.NETWORK
    )


    assert (
        smart.service_role
        == ServiceRole.STORAGE
    )



def test_asset_role_inference():

    server = create_asset(
        "atlas",
        AssetType.SERVER,
    )


    vm = create_asset(
        "debian-docker",
        AssetType.VM,
    )


    docker = create_asset(
        "docker.service",
        AssetType.SERVICE,
    )
    docker.metadata["hostname"] = "debian-docker"


    media = create_asset(
        "media-workload",
        AssetType.APPLICATION,
    )

    media.metadata["labels"] = {
        "org.opencontainers.image.description":
            "Self-hosted media server for photo and video streaming",
    }

    monitoring = create_asset(
        "metrics-workload",
        AssetType.APPLICATION,
    )

    monitoring.metadata["labels"] = {
        "org.opencontainers.image.description":
            "Monitoring and observability service exposing system metrics",
    }

    applications = [
        media,
        monitoring,
    ]


    # Applications explicitly belong to the discovered
    # Docker host. Role inference must never assume ownership
    # merely because applications exist in the same registry.
    for application in applications:
        application.metadata[
            "hostname"
        ] = "debian-docker"


    assets = [

        server,

        vm,

        docker,

        *applications,

    ]


    RoleInferenceService().infer(
        assets
    )


    assert (
        AssetRole.HYPERVISOR
        in server.asset_roles
    )


    assert (
        AssetRole.DOCKER_HOST
        in vm.asset_roles
    )


    assert (
        AssetRole.APPLICATION_SERVER
        in vm.asset_roles
    )


    assert (
        AssetRole.MEDIA_SERVER
        in vm.asset_roles
    )


    assert (
        AssetRole.MONITORING_NODE
        in vm.asset_roles
    )


    assert (
        AssetRole.APPLICATION_SERVER
        not in server.asset_roles
    )


    assert (
        AssetRole.MEDIA_SERVER
        not in server.asset_roles
    )


    assert (
        AssetRole.MONITORING_NODE
        not in server.asset_roles
    )
