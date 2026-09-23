from atlas.core.asset import (
    AssetType,
    AssetRole,
)

from atlas.core.relationship import (
    Relationship,
    RelationshipType,
)


class AssetGraphBuilder:

    def build(self, assets):

        relationships = []

        def add_relation(
            source,
            target,
            rel_type,
            discovered_by,
            confidence=1.0,
            evidence=None,
        ):

            if source.id == target.id:
                return

            relationship = Relationship(
                source=source.id,
                target=target.id,
                type=rel_type,
                confidence=confidence,
                evidence=evidence or [],
                metadata={
                    "discovered_by": discovered_by,
                },
            )

            source.add_relationship(
                relationship
            )

            if relationship not in relationships:
                relationships.append(
                    relationship
                )

        #
        # ---------------------------------------------------------
        # Asset groups
        # ---------------------------------------------------------
        #

        servers = [
            asset
            for asset in assets
            if asset.type == AssetType.SERVER
        ]

        vms = [
            asset
            for asset in assets
            if asset.type == AssetType.VM
        ]

        lxcs = [
            asset
            for asset in assets
            if asset.type == AssetType.LXC
        ]

        storages = [
            asset
            for asset in assets
            if asset.type == AssetType.STORAGE
        ]

        applications = [
            asset
            for asset in assets
            if asset.type == AssetType.APPLICATION
        ]

        services = [
            asset
            for asset in assets
            if asset.type == AssetType.SERVICE
        ]

        #
        # ---------------------------------------------------------
        # Proxmox topology
        # ---------------------------------------------------------
        #
        # Every Proxmox SERVER hosts its discovered VMs/LXCs.
        #

        for server in servers:

            for guest in vms + lxcs:

                add_relation(
                    server,
                    guest,
                    RelationshipType.HOSTS,
                    "proxmox_graph",
                    confidence=0.98,
                    evidence=[
                        "proxmox inventory",
                        "guest ownership",
                    ],
                )

        #
        # ---------------------------------------------------------
        # Proxmox storage topology
        # ---------------------------------------------------------
        #
        # Storage discovered on the Proxmox host belongs to that host.
        #

        for server in servers:

            for storage in storages:

                add_relation(
                    server,
                    storage,
                    RelationshipType.HOSTS,
                    "storage_graph",
                    confidence=0.98,
                    evidence=[
                        "storage discovery",
                        "host storage inventory",
                    ],
                )

        #
        # ---------------------------------------------------------
        # Docker host detection
        # ---------------------------------------------------------
        #
        # Do NOT depend on a specific runtime hostname.
        # Asset roles are the canonical source of infrastructure
        # semantics.
        #

        docker_hosts = [
            asset
            for asset in assets
            if AssetRole.DOCKER_HOST in asset.asset_roles
        ]

        #
        # ---------------------------------------------------------
        # Docker applications
        # ---------------------------------------------------------
        #
        # Every Docker application belongs to its Docker host.
        #

        for host in docker_hosts:

            for application in applications:

                add_relation(
                    host,
                    application,
                    RelationshipType.HOSTS,
                    "docker_graph",
                    confidence=0.90,
                    evidence=[
                        "docker host role",
                        "docker application inventory",
                    ],
                )

        #
        # ---------------------------------------------------------
        # System services
        # ---------------------------------------------------------
        #
        # Services discovered through systemd are attached to the
        # machine identified by their hostname.
        #

        hosts = [
            asset
            for asset in assets
            if asset.type in (
                AssetType.SERVER,
                AssetType.VM,
                AssetType.LXC,
            )
        ]

        for service in services:

            hostname = service.metadata.get(
                "hostname"
            )

            if not hostname:
                continue

            for host in hosts:

                if host.name != hostname:
                    continue

                add_relation(
                    host,
                    service,
                    RelationshipType.HOSTS,
                    "service_graph",
                    confidence=0.95,
                    evidence=[
                        "systemd service discovery",
                        "hostname match",
                    ],
                )

        #
        # ---------------------------------------------------------
        # Docker daemon service
        # ---------------------------------------------------------
        #
        # Find the real docker.service asset.
        #

        docker_daemons = [
            service
            for service in services
            if service.name.lower() in (
                "docker.service",
                "docker",
            )
        ]

        for docker_daemon in docker_daemons:

            hostname = docker_daemon.metadata.get(
                "hostname"
            )

            if not hostname:
                continue

            for host in hosts:

                if host.name != hostname:
                    continue

                #
                # Host provides Docker runtime.
                #

                add_relation(
                    host,
                    docker_daemon,
                    RelationshipType.PROVIDES,
                    "docker_host_graph",
                    confidence=0.98,
                    evidence=[
                        "docker.service discovery",
                        "hostname match",
                    ],
                )

                #
                # Docker daemon runs the discovered applications.
                #

                for application in applications:

                    add_relation(
                        docker_daemon,
                        application,
                        RelationshipType.RUNS,
                        "docker_runtime_graph",
                        confidence=0.95,
                        evidence=[
                            "docker.service discovery",
                            "docker application inventory",
                        ],
                    )

        #
        # ---------------------------------------------------------
        # Return graph
        # ---------------------------------------------------------
        #

        return relationships
