import logging

from atlas.services.assets.runtime import get_asset_registry

from atlas.providers.host import HostAssetProvider
from atlas.providers.docker import DockerAssetProvider
from atlas.providers.storage import StorageAssetProvider
from atlas.collectors.proxmox.host import ProxmoxHostDiscovery
from atlas.collectors.proxmox.guests import ProxmoxGuestDiscovery
from atlas.collectors.services.systemd import SystemdServiceCollector
from atlas.collectors.services.lxc import LXCServiceCollector

from atlas.services.assets.builder import AssetBuilder
from atlas.services.assets.persistence import AssetPersistenceService
from atlas.services.assets.role_inference import RoleInferenceService
from atlas.services.assets.graph_builder import AssetGraphBuilder
from atlas.services.assets.dependency_builder import DependencyBuilder
from atlas.services.assets.graph_service import AssetGraphService

from atlas.models.discovery import DiscoveryResult

from atlas.config.proxmox import (
    require_proxmox_host,
)


logger = logging.getLogger(__name__)


def _diagnostic(*parts):
    """
    Legacy development diagnostics.

    Normal production runs keep these at DEBUG level.
    Diagnostics containing ERROR remain visible as warnings.
    """

    message = " ".join(
        str(part)
        for part in parts
    )

    if "ERROR" in message.upper():
        logger.warning(
            "%s",
            message,
        )
    else:
        logger.debug(
            "%s",
            message,
        )


class DiscoveryKernel:

    def __init__(self):

        self.registry = get_asset_registry()

        self.persistence = AssetPersistenceService()
        self.role_inference = RoleInferenceService()

        self.builder = AssetBuilder()

        self.graph_builder = AssetGraphBuilder()
        self.dependency_builder = DependencyBuilder()
        self.graph_service = AssetGraphService()

        self.providers = [

            HostAssetProvider(),

        ]


        # Docker is an optional provider.
        #
        # A clean ATLAS host with neither Docker CLI nor Docker socket is
        # valid and must not instantiate a Docker client at all.
        #
        # Partial/configured Docker remains present so collect() can report
        # a genuine provider failure through the normal isolation boundary.
        if DockerAssetProvider.is_configured():

            self.providers.append(
                DockerAssetProvider()
            )


        self.providers.append(
            StorageAssetProvider()
        )


        for provider in self.providers:

            self.registry.register_provider(
                provider
            )


    def _discover_proxmox(self):

        assets = []


        #
        # Proxmox host
        #

        proxmox_host = (
            require_proxmox_host()
        )

        host = ProxmoxHostDiscovery(
            proxmox_host
        ).discover()


        host_asset = self.builder.from_proxmox_host(
            host
        )


        assets.append(
            host_asset
        )


        #
        # Proxmox guests
        #

        guests = ProxmoxGuestDiscovery(
            proxmox_host
        ).discover()


        for guest in guests:

            if guest["type"] == "VM":

                asset = self.builder.from_proxmox_vm(
                    guest
                )

            else:

                asset = self.builder.from_proxmox_lxc(
                    guest
                )


            assets.append(
                asset
            )


        return assets, guests


    def _discover_lxc_services(
        self,
        guests,
    ):

        assets = []


        for guest in guests:

            if guest["type"] != "LXC":
                continue


            services = LXCServiceCollector().collect(
                guest
            )


            for service in services:

                asset = self.builder.from_system_service(
                    service
                )


                assets.append(
                    asset
                )


        return assets


    def _discover_host_services(self):

        assets = []


        services = SystemdServiceCollector().collect()


        for service in services:

            asset = self.builder.from_system_service(
                service
            )


            assets.append(
                asset
            )


        return assets


    def discover(self):

        _diagnostic(
            "DEBUG PROVIDERS START"
        )

        discovery_errors = []

        successful_sources = []

        #
        # Clear previous runtime state
        #

        self.registry.clear()

        #
        # Standard providers
        #
        # Collect each provider exactly once and register
        # the resulting assets.
        #

        provider_assets = []

        for provider in self.providers:

            try:

                result = provider.collect()

                _diagnostic(
                    "DEBUG PROVIDER:",
                    provider.__class__.__name__,
                    "COUNT:",
                    len(result)
                )

                provider_errors = list(
                    getattr(
                        provider,
                        "errors",
                        [],
                    )
                    or []
                )

                if provider_errors:

                    for provider_error in provider_errors:

                        discovery_errors.append(
                            (
                                f"{provider.__class__.__name__}: "
                                f"{provider_error}"
                            )
                        )

                else:

                    successful_sources.append(
                        provider.__class__.__name__
                    )

                for asset in result:

                    _diagnostic(
                        "  ASSET:",
                        asset.id,
                        asset.type,
                        asset.name
                    )

                    provider_assets.append(asset)

            except Exception as exc:

                error = (
                    f"{provider.__class__.__name__}: "
                    f"{exc}"
                )

                discovery_errors.append(
                    error
                )

                _diagnostic(
                    "DEBUG PROVIDER ERROR:",
                    provider.__class__.__name__,
                    exc
                )

        #
        # Register standard provider assets
        #

        for asset in provider_assets:

            try:

                self.registry.register(
                    asset
                )

            except Exception as exc:

                discovery_errors.append(
                    (
                        "ProviderRegistration:"
                        f"{asset.id}: {exc}"
                    )
                )

                _diagnostic(
                    "DEBUG PROVIDER REGISTER ERROR:",
                    asset.id,
                    exc
                )

        #
        # Proxmox infrastructure
        #

        try:

            proxmox_assets, guests = (
                self._discover_proxmox()
            )

            for asset in proxmox_assets:

                self.registry.register(
                    asset
                )

            successful_sources.append(
                "Proxmox"
            )

            _diagnostic(
                "DEBUG PROXMOX ASSETS:",
                len(proxmox_assets)
            )

        except Exception as exc:

            discovery_errors.append(
                f"Proxmox: {exc}"
            )

            _diagnostic(
                "DEBUG PROXMOX ERROR:",
                exc
            )

            guests = []

        #
        # LXC services
        #

        try:

            lxc_services = (
                self._discover_lxc_services(
                    guests
                )
            )

            for asset in lxc_services:

                self.registry.register(
                    asset
                )

            successful_sources.append(
                "LXCServices"
            )

            _diagnostic(
                "DEBUG LXC SERVICES:",
                len(lxc_services)
            )

        except Exception as exc:

            discovery_errors.append(
                f"LXCServices: {exc}"
            )

            _diagnostic(
                "DEBUG LXC SERVICES ERROR:",
                exc
            )

        #
        # Host services
        #

        try:

            host_services = (
                self._discover_host_services()
            )

            for asset in host_services:

                self.registry.register(
                    asset
                )

            successful_sources.append(
                "HostServices"
            )

            _diagnostic(
                "DEBUG HOST SERVICES:",
                len(host_services)
            )

        except Exception as exc:

            discovery_errors.append(
                f"HostServices: {exc}"
            )

            _diagnostic(
                "DEBUG HOST SERVICES ERROR:",
                exc
            )

        #
        # Infer roles after complete discovery.
        #
        # Role inference requires the complete asset set so
        # infrastructure roles can be derived from discovered
        # services and applications.
        #

        discovered_assets = self.registry.assets()

        discovered_assets = self.role_inference.infer(
            discovered_assets
        )

        #
        # Persist discovered assets
        #

        for asset in discovered_assets:

            try:

                self.persistence.persist(
                    asset
                )

            except Exception as exc:

                _diagnostic(
                    "DEBUG PERSIST ERROR:",
                    asset.id,
                    exc
                )

        #
        # Build and persist asset graph
        #

        try:

            assets = self.registry.assets()

            graph_relationships = (
                self.graph_builder.build(
                    assets
                )
            )

            dependency_relationships = (
                self.dependency_builder.build(
                    assets
                )
            )

            relationships = (
                graph_relationships
                + dependency_relationships
            )

            self.graph_service.persist(
                relationships
            )

            _diagnostic(
                "ASSET GRAPH PERSISTED:",
                len(relationships)
            )

        except Exception as exc:

            _diagnostic(
                "DEBUG GRAPH ERROR:",
                exc
            )

        #
        # Discovery result
        #

        assets = self.registry.assets()

        _diagnostic(
            "DEBUG PROVIDERS END"
        )

        _diagnostic(
            "DISCOVERY REGISTRY ID:",
            id(self.registry)
        )

        _diagnostic(
            "DISCOVERY ASSETS:",
            len(assets)
        )

        for asset in assets:

            _diagnostic(
                asset.type,
                asset.name
            )

        complete = (
            len(discovery_errors)
            == 0
        )

        _diagnostic(
            "DISCOVERY COMPLETE:",
            complete
        )

        if discovery_errors:

            _diagnostic(
                "DISCOVERY ERRORS:",
                discovery_errors
            )

        return DiscoveryResult(
            assets=assets,
            providers=successful_sources,
            count=len(assets),
            complete=complete,
            errors=discovery_errors,
        )
