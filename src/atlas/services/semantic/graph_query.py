from __future__ import annotations

from collections import deque

from atlas.core.semantic import (
    SemanticEntityKind,
)

from atlas.services.semantic.entity_resolver import (
    SemanticEntityResolver,
)

from atlas.storage.graph_repository import (
    GraphRepository,
)


class SemanticGraphQueryService:
    """
    Technology-neutral semantic graph query.

    Inputs:

        entity
        relationship
        orientation
        depth

    The entity may resolve to:

        ASSET
        GROUP
        AMBIGUOUS
        NOT_FOUND

    GROUP queries operate over all discovered group members.

    This service contains no knowledge of Docker, Compose, Proxmox,
    Kubernetes, systemd, application names, host names or ID formats.
    """

    OUTGOING = "OUTGOING"
    INCOMING = "INCOMING"


    def __init__(
        self,
        registry,
        *,
        graph=None,
        entity_resolver=None,
    ):

        self.registry = registry

        self.graph = (
            graph
            or GraphRepository()
        )

        self.entity_resolver = (
            entity_resolver
            or SemanticEntityResolver(
                registry
            )
        )


    @staticmethod
    def _normalize_relationship(
        relationship,
    ) -> str | None:

        if relationship is None:
            return None

        name = getattr(
            relationship,
            "name",
            relationship,
        )

        value = str(
            name
        ).strip().upper()

        return value or None


    @staticmethod
    def _normalize_orientation(
        orientation,
    ) -> str:

        value = str(
            orientation
            or ""
        ).strip().upper()

        aliases = {
            "DOWNSTREAM":
                "OUTGOING",

            "UPSTREAM":
                "INCOMING",
        }

        value = aliases.get(
            value,
            value,
        )

        if value not in {
            "OUTGOING",
            "INCOMING",
        }:
            raise ValueError(
                "orientation must be "
                "OUTGOING or INCOMING"
            )

        return value


    def _asset_name(
        self,
        asset_id,
    ):

        asset = self.registry.get(
            asset_id
        )

        if asset is None:
            return None

        return asset.name


    def _relations(
        self,
        asset_id,
        orientation,
    ):

        if orientation == self.OUTGOING:

            return self.graph.get_children(
                asset_id
            )

        return self.graph.get_parents(
            asset_id
        )


    @staticmethod
    def _peer(
        relation,
        orientation,
    ):

        if orientation == "OUTGOING":

            return relation.get(
                "target"
            )

        return relation.get(
            "source"
        )


    def query(
        self,
        entity_query: str,
        *,
        relationship=None,
        orientation="OUTGOING",
        depth=1,
    ):

        orientation = (
            self._normalize_orientation(
                orientation
            )
        )

        relationship = (
            self._normalize_relationship(
                relationship
            )
        )

        depth = max(
            1,
            min(
                int(depth),
                20,
            ),
        )

        entity = (
            self.entity_resolver
            .resolve(
                entity_query
            )
        )

        # ----------------------------------------------------------
        # UNRESOLVED / AMBIGUOUS
        # ----------------------------------------------------------

        if (
            entity.kind
            == SemanticEntityKind.NOT_FOUND
        ):

            return {
                "status":
                    "NOT_FOUND",

                "entity":
                    entity.as_dict(),

                "relationship":
                    relationship,

                "orientation":
                    orientation,

                "depth":
                    depth,

                "count":
                    0,

                "results":
                    [],
            }

        if (
            entity.kind
            == SemanticEntityKind.AMBIGUOUS
        ):

            return {
                "status":
                    "AMBIGUOUS",

                "entity":
                    entity.as_dict(),

                "relationship":
                    relationship,

                "orientation":
                    orientation,

                "depth":
                    depth,

                "count":
                    0,

                "results":
                    [],
            }

        roots = list(
            entity.member_ids
        )

        # ASSET results normally contain exactly one member.
        # GROUP results may contain any number of discovered members.
        if not roots:

            return {
                "status":
                    "NOT_FOUND",

                "entity":
                    entity.as_dict(),

                "relationship":
                    relationship,

                "orientation":
                    orientation,

                "depth":
                    depth,

                "count":
                    0,

                "results":
                    [],
            }

        # ----------------------------------------------------------
        # GRAPH WALK
        # ----------------------------------------------------------

        queue = deque()

        for root_id in roots:

            queue.append(
                (
                    root_id,
                    root_id,
                    1,
                )
            )

        # Traversal state is root-aware.
        #
        # Two members of the same logical group may legitimately
        # reach the same graph node.
        visited = set()

        # Relationship identity is global so the final result does
        # not contain duplicate edges simply because several group
        # members reached the same relationship.
        seen_edges = set()

        results = []

        while queue:

            (
                root_id,
                current_id,
                current_depth,
            ) = queue.popleft()

            if current_depth > depth:
                continue

            state_key = (
                root_id,
                current_id,
                current_depth,
            )

            if state_key in visited:
                continue

            visited.add(
                state_key
            )

            for relation in self._relations(
                current_id,
                orientation,
            ):

                relation_type = (
                    str(
                        relation.get(
                            "type",
                            ""
                        )
                    )
                    .strip()
                    .upper()
                )

                if (
                    relationship is not None
                    and relation_type
                    != relationship
                ):
                    # A relationship-filtered graph query follows
                    # only that relationship family.
                    continue

                source = relation.get(
                    "source"
                )

                target = relation.get(
                    "target"
                )

                if not source or not target:
                    continue

                edge_key = (
                    source,
                    target,
                    relation_type,
                )

                if edge_key not in seen_edges:

                    seen_edges.add(
                        edge_key
                    )

                    results.append(
                        {
                            "source_asset_id":
                                source,

                            "source_name":
                                self._asset_name(
                                    source
                                ),

                            "target_asset_id":
                                target,

                            "target_name":
                                self._asset_name(
                                    target
                                ),

                            "relationship":
                                relation_type,

                            "orientation":
                                orientation,

                            "depth":
                                current_depth,

                            "root_member_id":
                                root_id,

                            "confidence":
                                float(
                                    relation.get(
                                        "confidence",
                                        0.0,
                                    )
                                    or 0.0
                                ),

                            "evidence":
                                list(
                                    relation.get(
                                        "evidence",
                                        [],
                                    )
                                    or []
                                ),
                        }
                    )

                if current_depth >= depth:
                    continue

                peer = self._peer(
                    relation,
                    orientation,
                )

                if not peer:
                    continue

                queue.append(
                    (
                        root_id,
                        peer,
                        current_depth + 1,
                    )
                )

        return {
            "status":
                "SUCCESS",

            "entity":
                entity.as_dict(),

            "relationship":
                relationship,

            "orientation":
                orientation,

            "depth":
                depth,

            "count":
                len(
                    results
                ),

            "results":
                results,
        }
