from atlas.core.asset import AssetType
from atlas.core.relationship import (
    Relationship,
    RelationshipType,
)


class DependencyBuilder:

    def build(
        self,
        assets,
    ):

        relationships = []

        applications = [
            asset
            for asset in assets
            if asset.type == AssetType.APPLICATION
        ]

        # ------------------------------------------------------------
        # Canonical application set
        # ------------------------------------------------------------

        canonical = {}

        for asset in applications:

            key = str(
                asset.id
            )

            canonical[key] = asset

        # ------------------------------------------------------------
        # Compose service index
        #
        # Identity is scoped by project because two projects may use
        # the same service name.
        # ------------------------------------------------------------

        compose_services = {}

        for asset in canonical.values():

            metadata = (
                asset.metadata
                or {}
            )

            project = metadata.get(
                "compose_project"
            )

            service = metadata.get(
                "compose_service"
            )

            if (
                not project
                or not service
            ):
                continue

            compose_services[
                (
                    str(project).strip().lower(),
                    str(service).strip().lower(),
                )
            ] = asset

        def add(
            source,
            target,
            rel_type,
            reason,
            confidence=0.99,
            evidence=None,
        ):

            if source.id == target.id:
                return

            # Avoid duplicate relationships.
            for existing in relationships:

                if (
                    existing.source == source.id
                    and existing.target == target.id
                    and existing.type == rel_type
                ):
                    return

            relationship = Relationship(
                source=source.id,
                target=target.id,
                type=rel_type,
                confidence=confidence,
                evidence=evidence or [],
                metadata={
                    "discovered_by": reason,
                },
            )

            source.add_relationship(
                relationship
            )

            relationships.append(
                relationship
            )

        # ------------------------------------------------------------
        # Docker Compose dependencies
        #
        # Docker exposes:
        #
        # com.docker.compose.depends_on =
        #   database:service_started:false,
        #   cache:service_started:false
        #
        # We resolve service names only inside the same Compose
        # project. No application identities are known here.
        # ------------------------------------------------------------

        for source in canonical.values():

            metadata = (
                source.metadata
                or {}
            )

            project = metadata.get(
                "compose_project"
            )

            labels = (
                metadata.get(
                    "labels"
                )
                or {}
            )

            depends_raw = labels.get(
                "com.docker.compose.depends_on"
            )

            if (
                not project
                or not depends_raw
            ):
                continue

            project_key = str(
                project
            ).strip().lower()

            dependencies = [
                item.strip()
                for item in str(
                    depends_raw
                ).split(",")
                if item.strip()
            ]

            for dependency in dependencies:

                # Compose encodes extra condition/restart metadata
                # after the service name.
                service_name = (
                    dependency.split(
                        ":",
                        1,
                    )[0]
                    .strip()
                    .lower()
                )

                if not service_name:
                    continue

                target = compose_services.get(
                    (
                        project_key,
                        service_name,
                    )
                )

                if target is None:
                    continue

                add(
                    source,
                    target,
                    RelationshipType.DEPENDS_ON,
                    "docker_compose",
                    confidence=0.99,
                    evidence=[
                        "docker compose depends_on label",
                        f"compose project: {project}",
                        f"compose service: {service_name}",
                    ],
                )

        return relationships
