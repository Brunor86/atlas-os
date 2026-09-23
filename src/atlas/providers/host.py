from atlas.core.asset import (
    Asset,
    AssetStatus,
    AssetType,
)

from atlas.core.provider import AssetProvider
from atlas.services.system import SystemService

import subprocess


class HostAssetProvider(AssetProvider):

    def __init__(self):
        self.service = SystemService()

    def collect(self) -> list[Asset]:

        system = self.service.get_info()

        virt = subprocess.run(
            [
                "systemd-detect-virt"
            ],
            capture_output=True,
            text=True,
        ).stdout.strip()

        #
        # If ATLAS is running inside a virtual machine,
        # Proxmox is the authoritative identity source.
        #
        # Therefore this provider must not create a
        # duplicate SERVER asset for the guest.
        #

        if virt and virt != "none":
            return []

        #
        # Bare-metal host
        #

        asset = Asset(
            id=f"server-{system.hostname}",
            name=system.hostname,
            type=AssetType.SERVER,
            status=AssetStatus.ONLINE,
            metadata={
                "virtualization": virt,
            },
        )

        return [
            asset
        ]
