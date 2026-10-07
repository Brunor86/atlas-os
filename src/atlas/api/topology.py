from fastapi import APIRouter




from atlas.services.assets.identity_reconciliation import (
    IdentityReconciliationService,
)

from atlas.services.assets.home_assistant_discovery import (
    HomeAssistantDiscoveryService,
)

from atlas.services.assets.network_discovery import (
    LocalNetworkDiscoveryService,
)

from atlas.services.assets.topology_map import (
    TopologyMapService,
)


router = APIRouter(
    prefix="/api/topology",
    tags=[
        "topology",
    ],
)


@router.get(
    "/map"
)
def topology_map():
    return (
        TopologyMapService()
        .snapshot()
    )


@router.get(
    "/network"
)
def topology_network(
    scan: bool = True,
):
    return (
        LocalNetworkDiscoveryService()
        .snapshot(
            active_scan=scan
        )
    )


@router.get(
    "/home-assistant"
)
def topology_home_assistant():
    return (
        HomeAssistantDiscoveryService()
        .snapshot()
    )


@router.get(
    "/identity"
)
def topology_identity(
    scan: bool = True,
):
    return (
        IdentityReconciliationService()
        .snapshot(
            active_scan=scan
        )
    )
