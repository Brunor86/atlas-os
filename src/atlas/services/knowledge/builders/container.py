from atlas.services.knowledge.builders.base import (
    KnowledgeBuilder,
)


class ContainerBuilder(KnowledgeBuilder):
    """
    Build container knowledge from the canonical Asset model.

    Product identity, topology and dependencies are discovered before
    Knowledge is built. This layer only translates those facts into a
    human-readable KnowledgeCard.
    """

    @staticmethod
    def _relationship_kind(
        relationship,
    ) -> str:

        value = (
            getattr(
                relationship,
                "type",
                None,
            )
            or getattr(
                relationship,
                "relationship_type",
                None,
            )
        )

        if value is None:
            return ""

        name = getattr(
            value,
            "name",
            None,
        )

        if name:
            return str(
                name
            ).upper()

        value = getattr(
            value,
            "value",
            value,
        )

        return str(
            value
        ).upper()

    @staticmethod
    def _asset_relationships(
        asset,
    ):

        relationships = getattr(
            asset,
            "relationships",
            None,
        )

        if relationships is None:
            relationships = getattr(
                asset,
                "relations",
                None,
            )

        if relationships is None:
            return []

        if isinstance(
            relationships,
            dict,
        ):
            return list(
                relationships.values()
            )

        return list(
            relationships
        )

    @staticmethod
    def _resolve_target_name(
        graph,
        target_id,
    ):

        if not target_id:
            return None

        topology = getattr(
            graph,
            "topology",
            None,
        )

        registry = getattr(
            topology,
            "assets",
            None,
        )

        if registry is not None:

            for method_name in (
                "get_asset",
                "get",
            ):

                method = getattr(
                    registry,
                    method_name,
                    None,
                )

                if not callable(
                    method
                ):
                    continue

                try:
                    target = method(
                        target_id
                    )
                except Exception:
                    target = None

                if target is not None:
                    return (
                        getattr(
                            target,
                            "name",
                            None,
                        )
                        or str(target_id)
                    )

        resolver = getattr(
            graph,
            "resolver",
            None,
        )

        if resolver is not None:

            for method_name in (
                "resolve_dependency",
                "resolve_docker_id",
            ):

                method = getattr(
                    resolver,
                    method_name,
                    None,
                )

                if not callable(
                    method
                ):
                    continue

                try:
                    target = method(
                        target_id
                    )
                except Exception:
                    target = None

                if target is not None:
                    return (
                        getattr(
                            target,
                            "name",
                            None,
                        )
                        or str(target_id)
                    )

        return str(
            target_id
        )

    def build(
        self,
        asset,
        card,
        graph,
    ):

        metadata = (
            getattr(
                asset,
                "metadata",
                None,
            )
            or {}
        )

        labels = (
            metadata.get(
                "labels"
            )
            or {}
        )

        if not isinstance(
            labels,
            dict,
        ):
            labels = {}

        # ------------------------------------------------------------
        # Runtime-discovered identity
        # ------------------------------------------------------------

        title = (
            labels.get(
                "org.opencontainers.image.title"
            )
            or metadata.get(
                "compose_service"
            )
            or getattr(
                asset,
                "name",
                None,
            )
            or "Application"
        )

        card.summary = (
            f"{title} running as application container."
        )

        # ------------------------------------------------------------
        # Canonical inferred roles
        # ------------------------------------------------------------

        roles = (
            getattr(
                asset,
                "asset_roles",
                None,
            )
            or set()
        )

        for role in sorted(
            roles,
            key=lambda item: (
                getattr(
                    item,
                    "name",
                    str(item),
                )
            ),
        ):

            role_name = getattr(
                role,
                "name",
                str(role),
            )

            if role_name not in card.roles:
                card.roles.append(
                    role_name
                )

        if not card.roles:
            card.roles.append(
                "APPLICATION_CONTAINER"
            )

        # ------------------------------------------------------------
        # Runtime observations
        # ------------------------------------------------------------

        runtime = metadata.get(
            "runtime"
        )

        image = metadata.get(
            "image"
        )

        compose_project = metadata.get(
            "compose_project"
        )

        compose_service = metadata.get(
            "compose_service"
        )

        criticality = getattr(
            getattr(
                asset,
                "criticality",
                None,
            ),
            "name",
            None,
        )

        observations = (
            (
                "Runtime",
                runtime,
            ),
            (
                "Image",
                image,
            ),
            (
                "Compose project",
                compose_project,
            ),
            (
                "Compose service",
                compose_service,
            ),
            (
                "Criticality",
                criticality,
            ),
        )

        for label, value in observations:

            if value in (
                None,
                "",
            ):
                continue

            item = (
                f"{label}: {value}"
            )

            if item not in card.observations:
                card.observations.append(
                    item
                )

        # ------------------------------------------------------------
        # Dependencies already discovered by topology builders.
        # Knowledge does not invent dependencies.
        # ------------------------------------------------------------

        for relationship in self._asset_relationships(
            asset
        ):

            if (
                self._relationship_kind(
                    relationship
                )
                != "DEPENDS_ON"
            ):
                continue

            target_id = getattr(
                relationship,
                "target",
                None,
            )

            target_name = (
                self._resolve_target_name(
                    graph,
                    target_id,
                )
            )

            if not target_name:
                continue

            if (
                target_name
                not in card.application_dependencies
            ):
                card.application_dependencies.append(
                    target_name
                )

        return card
