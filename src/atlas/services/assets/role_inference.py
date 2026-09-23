from atlas.core.asset import (
    Asset,
    AssetType,
    AssetRole,
    ServiceRole,
)

from atlas.services.assets.application_classifier import (
    ApplicationClassifier,
)
from atlas.services.assets.service_classifier import (
    ServiceClassifier,
)


class RoleInferenceService:

    def __init__(self):

        self.service_classifier = (
            ServiceClassifier()
        )

        self.application_classifier = (
            ApplicationClassifier()
        )

    def infer(self, assets):

        # ============================================================
        # RESET
        # ============================================================

        for asset in assets:
            asset.asset_roles.clear()
            asset.role_evidence.clear()

        # ============================================================
        # PHASE 1
        # Intrinsic inference
        # ============================================================

        for asset in assets:

            if asset.type == AssetType.SERVICE:
                self._infer_service_role(asset)

            elif asset.type == AssetType.APPLICATION:
                self._infer_application_role(asset)

            else:
                self._infer_asset_roles(
                    asset,
                    assets,
                )

        # ============================================================
        # PHASE 2
        # Infrastructure discovery
        # ============================================================

        for asset in assets:

            if asset.type not in {
                AssetType.SERVER,
                AssetType.VM,
                AssetType.LXC,
            }:
                continue

            self._infer_docker_host_role(
                asset,
                assets,
            )

        # ============================================================
        # PHASE 3
        # Workload propagation
        # ============================================================

        for asset in assets:

            if asset.type not in {
                AssetType.SERVER,
                AssetType.VM,
                AssetType.LXC,
            }:
                continue

            self._infer_discovered_workload_roles(
                asset,
                assets,
            )

        return assets

    # ================================================================
    # HELPERS
    # ================================================================

    def _add_role(
        self,
        asset: Asset,
        role: AssetRole,
        evidence: str,
    ):

        asset.asset_roles.add(role)

        if evidence not in asset.role_evidence:
            asset.role_evidence.append(evidence)

    # ================================================================
    # SERVICE ROLE
    # ================================================================

    def _infer_service_role(
        self,
        asset: Asset,
    ):

        classification = (
            self.service_classifier.classify(
                asset.name,
                asset.metadata,
            )
        )

        asset.service_role = (
            classification.role
        )

        asset.service_importance = (
            classification.importance
        )

    # ================================================================
    # APPLICATION ROLE
    # ================================================================

    def _infer_application_role(
        self,
        asset: Asset,
    ):

        classification = (
            self.application_classifier.classify(
                asset.name,
                asset.metadata,
            )
        )

        if classification.role is None:
            return

        evidence = (
            classification.reason
        )

        if classification.evidence:
            evidence += (
                ": "
                + ", ".join(
                    classification.evidence
                )
            )

        self._add_role(
            asset,
            classification.role,
            evidence,
        )

    # ================================================================
    # DOCKER HOST
    # ================================================================

    def _infer_docker_host_role(
        self,
        asset,
        assets,
    ):

        if asset.type not in {
            AssetType.SERVER,
            AssetType.VM,
            AssetType.LXC,
        }:
            return

        for service in assets:

            if service.type != AssetType.SERVICE:
                continue

            hostname = (
                service.metadata.get(
                    "hostname"
                )
                if service.metadata
                else None
            )

            if hostname != asset.name:
                continue

            if (
                service.service_role
                != ServiceRole.CONTAINER_RUNTIME
            ):
                continue

            self._add_role(
                asset,
                AssetRole.DOCKER_HOST,
                "container_runtime_service_detected",
            )

            return

    # ================================================================
    # WORKLOAD OWNERSHIP
    # ================================================================

    def _belongs_to(
        self,
        workload: Asset,
        host: Asset,
    ) -> bool:

        metadata = workload.metadata or {}

        values = (
            metadata.get("hostname"),
            metadata.get("host"),
            metadata.get("host_name"),
            metadata.get("parent"),
            metadata.get("parent_id"),
            metadata.get("container_host"),
            metadata.get("docker_host"),
            metadata.get("host_id"),
        )

        host_ids = {
            str(host.id).lower(),
            str(host.name).lower(),
        }

        for value in values:

            if value is None:
                continue

            if str(value).lower() in host_ids:
                return True

        for relationship in (
            getattr(
                workload,
                "relationships",
                None,
            )
            or []
        ):

            source = getattr(
                relationship,
                "source",
                None,
            )

            target = getattr(
                relationship,
                "target",
                None,
            )

            source_id = getattr(
                source,
                "id",
                source,
            )

            target_id = getattr(
                target,
                "id",
                target,
            )

            if str(source_id).lower() in host_ids:
                return True

            if str(target_id).lower() in host_ids:
                return True

        return False

    # ================================================================
    # WORKLOAD PROPAGATION
    # ================================================================

    def _infer_discovered_workload_roles(
        self,
        asset,
        assets,
    ):

        if AssetRole.DOCKER_HOST not in asset.asset_roles:
            return

        applications = [
            application
            for application in assets
            if (
                application.type
                == AssetType.APPLICATION
                and self._belongs_to(
                    application,
                    asset,
                )
            )
        ]

        if not applications:
            return

        # ------------------------------------------------------------
        # MEDIA
        # ------------------------------------------------------------

        if any(
            AssetRole.MEDIA_SERVER
            in application.asset_roles
            for application in applications
        ):

            self._add_role(
                asset,
                AssetRole.MEDIA_SERVER,
                "workload_media_detected",
            )

        # ------------------------------------------------------------
        # MONITORING
        # ------------------------------------------------------------

        if any(
            AssetRole.MONITORING_NODE
            in application.asset_roles
            for application in applications
        ):

            self._add_role(
                asset,
                AssetRole.MONITORING_NODE,
                "workload_monitoring_detected",
            )

        # ------------------------------------------------------------
        # APPLICATION SERVER
        # ------------------------------------------------------------

        if applications:

            self._add_role(
                asset,
                AssetRole.APPLICATION_SERVER,
                "workload_application_detected",
            )

    # ================================================================
    # INFRASTRUCTURE ROLES
    # ================================================================

    def _infer_asset_roles(
        self,
        asset: Asset,
        assets,
    ):

        if asset.type not in {
            AssetType.SERVER,
            AssetType.VM,
            AssetType.LXC,
        }:
            return

        # ------------------------------------------------------------
        # HYPERVISOR
        # ------------------------------------------------------------

        if asset.type == AssetType.SERVER:

            has_virtualization = any(
                candidate.type in {
                    AssetType.VM,
                    AssetType.LXC,
                }
                for candidate in assets
            )

            if has_virtualization:

                self._add_role(
                    asset,
                    AssetRole.HYPERVISOR,
                    "virtualization_topology_detected",
                )

        # ------------------------------------------------------------
        # PROVIDER ROLE METADATA
        # ------------------------------------------------------------

        metadata = asset.metadata or {}

        roles = metadata.get(
            "roles",
            [],
        )

        if isinstance(
            roles,
            str,
        ):
            roles = [roles]

        for role in roles:

            try:

                self._add_role(
                    asset,
                    AssetRole(role),
                    "provider_role_metadata",
                )

            except ValueError:
                continue

        # ------------------------------------------------------------
        # ONLY EXPLICIT WORKLOAD OWNERSHIP
        # ------------------------------------------------------------

        hosted = [
            application
            for application in assets
            if (
                application.type
                == AssetType.APPLICATION
                and self._belongs_to(
                    application,
                    asset,
                )
            )
        ]

        if not hosted:
            return

        # ------------------------------------------------------------
        # APPLICATION SERVER
        # ------------------------------------------------------------

        self._add_role(
            asset,
            AssetRole.APPLICATION_SERVER,
            "application_workload_detected",
        )

        # ------------------------------------------------------------
        # MEDIA
        # ------------------------------------------------------------

        if any(
            AssetRole.MEDIA_SERVER
            in application.asset_roles
            for application in hosted
        ):

            self._add_role(
                asset,
                AssetRole.MEDIA_SERVER,
                "media_workload_detected",
            )

        # ------------------------------------------------------------
        # MONITORING
        # ------------------------------------------------------------

        if any(
            AssetRole.MONITORING_NODE
            in application.asset_roles
            for application in hosted
        ):

            self._add_role(
                asset,
                AssetRole.MONITORING_NODE,
                "monitoring_workload_detected",
            )

        # ------------------------------------------------------------
        # DATABASE
        # ------------------------------------------------------------

        if any(
            AssetRole.DATABASE_SERVER
            in application.asset_roles
            for application in hosted
        ):

            self._add_role(
                asset,
                AssetRole.DATABASE_SERVER,
                "database_workload_detected",
            )

        # ------------------------------------------------------------
        # CACHE
        # ------------------------------------------------------------

        if any(
            AssetRole.CACHE_SERVICE
            in application.asset_roles
            for application in hosted
        ):

            self._add_role(
                asset,
                AssetRole.CACHE_SERVICE,
                "cache_workload_detected",
            )
