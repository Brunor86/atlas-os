from dataclasses import dataclass

from atlas.core.asset import (
    ServiceImportance,
    ServiceRole,
)


@dataclass
class ServiceClassification:

    role: ServiceRole
    importance: ServiceImportance
    reason: str


class ServiceClassifier:
    """
    Classify the technical role of an operating-system service.

    Technical role and operational importance are deliberately separate.

    A service may be identifiable as a database, network service, container
    runtime, monitoring component, etc. without ATLAS assuming that the
    service is operationally critical.

    Importance must come from explicit metadata/policy. Missing or invalid
    importance therefore falls back to the neutral SYSTEM value.
    """

    def classify(
        self,
        name: str,
        metadata: dict | None = None,
    ) -> ServiceClassification:

        metadata = metadata or {}

        explicit_role = metadata.get(
            "service_role"
        )

        explicit_importance = metadata.get(
            "importance"
        )

        role = self._parse_role(
            explicit_role
        )

        if role is None:

            role = self._role_from_metadata(
                metadata
            )

            if role == ServiceRole.SYSTEM:

                role = self._role_from_name(
                    name
                )

        importance = self._parse_importance(
            explicit_importance
        )

        if importance is None:

            importance = (
                ServiceImportance.SYSTEM
            )

        default_reason = (
            "explicit metadata classification"
            if (
                explicit_role is not None
                or explicit_importance is not None
            )
            else "technical role inference"
        )

        return ServiceClassification(
            role=role,
            importance=importance,
            reason=metadata.get(
                "classification_reason",
                default_reason,
            ),
        )

    def _parse_role(
        self,
        value,
    ) -> ServiceRole | None:
        """
        Resolve declarative service-role metadata.

        ServiceRole uses Enum.auto(), so declarative strings must be
        resolved by enum member name rather than by Enum(value).
        """

        if value is None:
            return None

        if isinstance(
            value,
            ServiceRole,
        ):
            return value

        normalized = str(
            value
        ).strip().upper()

        if not normalized:
            return ServiceRole.SYSTEM

        try:
            return ServiceRole[
                normalized
            ]
        except KeyError:
            return ServiceRole.SYSTEM

    def _parse_importance(
        self,
        value,
    ) -> ServiceImportance | None:
        """
        Resolve declarative service-importance metadata.

        Missing importance means "not declared". Invalid metadata must never
        cause ATLAS to guess importance from service identity or role.
        """

        if value is None:
            return None

        if isinstance(
            value,
            ServiceImportance,
        ):
            return value

        normalized = str(
            value
        ).strip().upper()

        if not normalized:
            return ServiceImportance.SYSTEM

        try:
            return ServiceImportance[
                normalized
            ]
        except KeyError:
            return ServiceImportance.SYSTEM

    def _role_from_name(
        self,
        name: str,
    ) -> ServiceRole:

        value = str(
            name
            or ""
        ).strip().lower()

        #
        # Portable technology semantics only.
        #
        # These terms identify what a service does. They do not express
        # how important that service is in a particular installation.
        #

        if any(
            term in value
            for term in (
                "docker",
                "containerd",
                "podman",
            )
        ):
            return ServiceRole.CONTAINER_RUNTIME

        if any(
            term in value
            for term in (
                "network",
                "ssh",
                "tailscale",
                "wireguard",
                "vpn",
            )
        ):
            return ServiceRole.NETWORK

        if any(
            term in value
            for term in (
                "smart",
                "storage",
                "mount",
            )
        ):
            return ServiceRole.STORAGE

        if any(
            term in value
            for term in (
                "collector",
                "exporter",
                "monitor",
                "metrics",
                "telemetry",
            )
        ):
            return ServiceRole.MONITORING

        if any(
            term in value
            for term in (
                "postgres",
                "mysql",
                "mariadb",
                "mongo",
            )
        ):
            return ServiceRole.DATABASE

        if any(
            term in value
            for term in (
                "firewall",
                "nftables",
                "iptables",
                "fail2ban",
            )
        ):
            return ServiceRole.SECURITY

        if any(
            term in value
            for term in (
                "cron",
                "timer",
            )
        ):
            return ServiceRole.TIMER

        return ServiceRole.SYSTEM

    def _role_from_metadata(
        self,
        metadata: dict,
    ) -> ServiceRole:

        category = str(
            metadata.get(
                "category",
                "",
            )
        ).lower()

        role = str(
            metadata.get(
                "role",
                "",
            )
        ).lower()

        capabilities = {
            str(value).lower()
            for value in metadata.get(
                "capabilities",
                [],
            )
        }

        value = " ".join(
            [
                category,
                role,
                " ".join(
                    capabilities
                ),
            ]
        )

        if "database" in value:
            return ServiceRole.DATABASE

        if (
            "container" in value
            or "runtime" in value
        ):
            return ServiceRole.CONTAINER_RUNTIME

        if (
            "monitor" in value
            or "observability" in value
            or "metrics" in value
        ):
            return ServiceRole.MONITORING

        if (
            "management" in value
            or "administration" in value
        ):
            return ServiceRole.MANAGEMENT

        if "storage" in value:
            return ServiceRole.STORAGE

        if "network" in value:
            return ServiceRole.NETWORK

        if "security" in value:
            return ServiceRole.SECURITY

        if (
            "timer" in value
            or "scheduled" in value
        ):
            return ServiceRole.TIMER

        return ServiceRole.SYSTEM
