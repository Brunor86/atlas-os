import logging

from atlas.core.provider import AssetProvider

from atlas.config.proxmox import (
    is_proxmox_configured,
    require_proxmox_host,
)

from atlas.core.asset import (
    Asset,
    AssetType,
    AssetStatus,
    Criticality,
    Capability,
)

from atlas.core.identity import AssetIdentity
from atlas.core.identity_resolver import generate_asset_id
from atlas.services.telemetry import TelemetryService
from atlas.collectors.proxmox.smart import ProxmoxSmartCollector
from atlas.services.observations.smart import SmartObservationBuilder


logger = logging.getLogger(__name__)


class StorageAssetProvider(AssetProvider):

    def __init__(
        self,
        telemetry: TelemetryService | None = None,
    ):
        self.telemetry = (
            telemetry
            or TelemetryService()
        )

        self.smart_observations = (
            SmartObservationBuilder()
        )

        self.errors = []

    def collect(self):

        assets = []

        #
        # Per-cycle source errors.
        #
        # A provider may still return useful partial assets while
        # declaring that its inventory is not authoritative.
        #
        self.errors = []

        disks = self.telemetry.block_devices()

        #
        # ----------------------------------------------------------
        # Local / virtual storage
        # ----------------------------------------------------------
        #

        for disk in disks:

            device = disk.get("device")
            model = disk.get("model", "").strip()
            serial = disk.get("serial", "").strip()

            if not device:
                continue

            #
            # QEMU virtual disks cannot expose the physical SMART
            # data of the underlying Proxmox disk.
            #
            if model.upper() == "QEMU HARDDISK":
                continue

            identity = AssetIdentity(
                serial=serial or None,
                model=model or None,
                vendor=None,
            )

            asset = Asset(
                id=generate_asset_id(
                    "storage",
                    identity,
                ),
                name=model or disk.get("name", device),
                type=AssetType.STORAGE,
                status=AssetStatus.ONLINE,
                criticality=Criticality.MEDIUM,
                identity=identity,
                capabilities={
                    Capability.SMART,
                    Capability.TEMPERATURE,
                },
                metadata={
                    "device": device,
                    "name": disk.get("name"),
                    "size": disk.get("size"),
                },
            )

            assets.append(asset)

        #
        # ----------------------------------------------------------
        # Physical storage exposed by Proxmox
        # ----------------------------------------------------------
        #

        # A completely unconfigured optional Proxmox provider is
        # absent, not failed. Partial configuration still reaches
        # the normal failure-isolation boundary.
        if not is_proxmox_configured():
            return assets

        try:

            smart_infos = (
                ProxmoxSmartCollector(
                    require_proxmox_host(),
                    "/dev/sda",
                ).collect()
            )

            for smart in smart_infos:

                identity = AssetIdentity(
                    serial=smart.serial or None,
                    model=smart.model or None,
                    vendor=smart.vendor or None,
                )

                asset = Asset(
                    id=generate_asset_id(
                        "storage",
                        identity,
                    ),
                    name=smart.model or smart.device,
                    type=AssetType.STORAGE,
                    status=AssetStatus.ONLINE,
                    criticality=Criticality.MEDIUM,
                    identity=identity,
                    capabilities={
                        Capability.SMART,
                        Capability.TEMPERATURE,
                    },
                    metadata={
                        "device": smart.device,
                        "model": smart.model,
                        "serial": smart.serial,
                        "vendor": smart.vendor,
                        "firmware": smart.firmware,
                        "temperature_c":
                            smart.temperature,
                        "power_on_hours":
                            smart.power_on_hours,
                        "health": smart.health,
                        "smart_available":
                            smart.smart_available,
                        "smart_passed":
                            smart.smart_passed,
                        "source": "proxmox-smart",
                    },
                )

                observations = (
                    self.smart_observations.build(
                        asset.id,
                        smart,
                    )
                )

                for observation in observations:
                    asset.add_observation(
                        observation
                    )

                assets.append(asset)

        except Exception as exc:

            self.errors.append(
                f"Proxmox SMART: {exc}"
            )

            logger.warning(
                "Storage Proxmox SMART unavailable: %s",
                exc,
            )

        return assets
