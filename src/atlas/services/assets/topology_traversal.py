from atlas.storage.graph_repository import GraphRepository
from atlas.storage.asset_repository import AssetRepository
from atlas.services.knowledge.asset_resolver import AssetResolver

from atlas.core.relationship import (
    RelationshipType,
    is_operational_relationship,
    relationship_weight,
    relationship_impact_score,
)

from atlas.core.asset import (
    AssetType,
    ServiceImportance,
)


class TopologyTraversalService:

    def __init__(
        self,
        registry=None,
    ):

        self.registry = registry

        self.graph = GraphRepository()

        # AssetRepository remains the compatibility layer used
        # by topology identity resolution.
        self.assets = AssetRepository()

        if registry is None:

            from atlas.services.assets.runtime import (
                get_asset_registry,
            )

            registry = get_asset_registry()

        self.registry = registry

        self.resolver = AssetResolver(
            registry
        )





    # ------------------------------------------------------------
    # DIRECT TOPOLOGY COMPATIBILITY API
    # ------------------------------------------------------------
    #
    # GraphService historically exposes direct one-hop graph
    # relationships through:
    #
    #   get_dependencies()
    #   get_dependents()
    #   get_neighbors()
    #
    # Traversal semantics now live in TopologyTraversalService,
    # so retain those direct contracts here while delegating the
    # persisted relationship shape to GraphRepository.
    #
    # Relationship direction:
    #
    #   dependency:
    #       asset -> target
    #       GraphRepository.get_children()
    #
    #   dependent:
    #       source -> asset
    #       GraphRepository.get_parents()
    #
    # The returned dictionaries intentionally remain unchanged:
    # source, target, type, metadata, confidence, evidence, ...
    #

    def get_dependencies(
        self,
        asset_id,
    ):

        resolved_asset_id = (
            self._resolve_graph_asset_id(
                asset_id
            )
        )

        return self.graph.get_children(
            resolved_asset_id
        )


    def get_dependents(
        self,
        asset_id,
    ):

        resolved_asset_id = (
            self._resolve_graph_asset_id(
                asset_id
            )
        )

        return self.graph.get_parents(
            resolved_asset_id
        )


    def get_neighbors(
        self,
        asset_id,
    ):

        resolved_asset_id = (
            self._resolve_graph_asset_id(
                asset_id
            )
        )

        return self.graph.get_neighbors(
            resolved_asset_id
        )


    def upstream(
        self,
        asset_id,
        depth=5,
    ):

        # Resolve the public/logical asset identity to the
        # canonical graph identity before traversal.
        asset_id = self._resolve_graph_asset_id(
            asset_id
        )

        visited = set()
        result = []

        self._walk_up(
            asset_id,
            visited,
            result,
            depth,
        )

        return result



    def downstream(
        self,
        asset_id,
        depth=5,
    ):

        # Resolve the public/logical asset identity to the
        # canonical graph identity before traversal.
        asset_id = self._resolve_graph_asset_id(
            asset_id
        )

        visited = set()
        result = []

        self._walk_down(
            asset_id,
            visited,
            result,
            depth,
        )

        return result



    def _resolve_graph_asset_id(
        self,
        asset_id,
    ):
        """
        Resolve a public/logical asset identity to the canonical
        asset ID used by the topology graph.

        Resolution order:

        1. Use the supplied ID directly if it already exists in graph.
        2. Resolve the supplied value as an AssetRepository ID.
        3. Resolve by exact asset name.
        4. Among same-name assets, prefer the representation
           actually connected to the topology graph.
        """

        # ------------------------------------------------------------
        # 1. Direct graph identity
        # ------------------------------------------------------------

        try:
            if (
                self.graph.get_parents(asset_id)
                or self.graph.get_children(asset_id)
            ):
                return asset_id
        except Exception:
            pass


        # ------------------------------------------------------------
        # 2. Try AssetRepository ID lookup
        # ------------------------------------------------------------

        asset = None

        try:
            asset = self.assets.get_asset(
                asset_id
            )
        except Exception:
            asset = None


        # ------------------------------------------------------------
        # 3. If not found by ID, resolve by exact asset name
        # ------------------------------------------------------------

        candidates = []

        try:
            all_assets = self.assets.get_all_assets()

            for candidate in all_assets:

                candidate_id = candidate.id
                candidate_name = candidate.name

                if (
                    candidate_id == asset_id
                    or candidate_name.lower() == str(asset_id).lower()
                ):
                    candidates.append(candidate)

        except Exception:
            return asset_id


        # If repository lookup found an asset, include it.
        if asset is not None:
            if not any(
                candidate.id == asset.id
                for candidate in candidates
            ):
                candidates.insert(
                    0,
                    asset,
                )


        if not candidates:
            return asset_id


        # ------------------------------------------------------------
        # 4. Prefer candidate connected to graph
        # ------------------------------------------------------------

        graph_candidates = []

        for candidate in candidates:

            candidate_id = candidate.id

            try:
                parents = self.graph.get_parents(
                    candidate_id
                )

                children = self.graph.get_children(
                    candidate_id
                )

                if parents or children:
                    graph_candidates.append(
                        candidate_id
                    )

            except Exception:
                continue


        if graph_candidates:

            # Prefer the canonical domain resolver when this service
            # was created through its normal constructor.
            #
            # Some focused traversal tests intentionally construct a
            # minimal service instance. In that case graph evidence is
            # sufficient and we must not depend on provider-specific
            # ID formats.
            resolver = getattr(
                self,
                "resolver",
                None,
            )

            canonical = None

            if resolver is not None:

                try:
                    canonical = resolver.resolve(
                        asset_id
                    )
                except Exception:
                    canonical = None

            if (
                canonical is not None
                and canonical.id
                in graph_candidates
            ):

                resolved = canonical.id

            else:

                # Prefer the representation with the strongest actual
                # participation in the graph.
                def graph_degree(
                    candidate_id,
                ):

                    try:

                        parents = (
                            self.graph
                            .get_parents(
                                candidate_id
                            )
                        )

                        children = (
                            self.graph
                            .get_children(
                                candidate_id
                            )
                        )

                        return (
                            len(parents)
                            + len(children)
                        )

                    except Exception:

                        return 0

                resolved = max(
                    graph_candidates,
                    key=lambda candidate_id: (
                        graph_degree(
                            candidate_id
                        ),
                        candidate_id,
                    ),
                )

            if resolved != asset_id:

                print(
                    "TOPOLOGY ID RESOLVED:",
                    asset_id,
                    "->",
                    resolved,
                )

            return resolved


        # ------------------------------------------------------------
        # 5. No graph-connected representation found
        # ------------------------------------------------------------

        return candidates[0].id

    def _asset_for_id(
        self,
        asset_id,
    ):
        """
        Resolve an asset for topology semantics without assuming how
        the service instance was constructed.

        Runtime registry is preferred. AssetRepository is retained as
        the compatibility source for persisted topology consumers and
        minimal traversal fixtures.
        """

        registry = getattr(
            self,
            "registry",
            None,
        )

        if registry is not None:

            getter = getattr(
                registry,
                "get",
                None,
            )

            if callable(getter):

                try:
                    asset = getter(
                        asset_id
                    )
                except Exception:
                    asset = None

                if asset is not None:
                    return asset

        repository = getattr(
            self,
            "assets",
            None,
        )

        if repository is not None:

            getter = getattr(
                repository,
                "get_asset",
                None,
            )

            if callable(getter):

                try:
                    asset = getter(
                        asset_id
                    )
                except Exception:
                    asset = None

                if asset is not None:
                    return asset

        return None


    def _is_system_service(
        self,
        asset_id,
    ):
        """
        Determine system-service semantics from the Asset domain
        model.

        Unknown graph nodes are not guessed from IDs or names.
        """

        asset = self._asset_for_id(
            asset_id
        )

        if asset is None:
            return False

        return (
            asset.type
            == AssetType.SERVICE
            and asset.service_importance
            == ServiceImportance.SYSTEM
        )



    def _walk_up(
        self,
        asset_id,
        visited,
        result,
        depth,
        current_depth=1,
    ):
        if depth <= 0:
            return

        for rel in self.graph.get_parents(asset_id):

            source = rel["source"]

            if source in visited:
                continue

            visited.add(source)

            relationship = rel.get("type")

            try:
                relationship_type = RelationshipType[relationship]
                weight = relationship_impact_score(
                    relationship_type
                )
            except (KeyError, TypeError):
                weight = 1

            result.append(
                {
                    "asset_id": source,
                    "relationship": relationship,
                    "direction": "UPSTREAM",
                    "weight": weight,
                    "depth": current_depth,
                    "impact_score": weight / current_depth,
                    "confidence": rel.get(
                        "confidence",
                        0.0,
                    ),
                    "evidence": rel.get(
                        "evidence",
                        [],
                    ),
                }
            )

            self._walk_up(
                source,
                visited,
                result,
                depth - 1,
                current_depth + 1,
            )


    def _walk_down(
        self,
        asset_id,
        visited,
        result,
        depth,
        current_depth=1,
    ):
        if depth <= 0:
            return

        for rel in self.graph.get_children(asset_id):

            target = rel["target"]

            if target in visited:
                continue

            visited.add(target)

            relationship = rel.get("type")

            try:
                relationship_type = RelationshipType[relationship]
                weight = relationship_impact_score(
                    relationship_type
                )
            except (KeyError, TypeError):
                weight = 1

            result.append(
                {
                    "asset_id": target,
                    "relationship": relationship,
                    "direction": "DOWNSTREAM",
                    "weight": weight,
                    "depth": current_depth,
                    "impact_score": weight / current_depth,
                    "confidence": rel.get(
                        "confidence",
                        0.0,
                    ),
                    "evidence": rel.get(
                        "evidence",
                        [],
                    ),
                }
            )

            self._walk_down(
                target,
                visited,
                result,
                depth - 1,
                current_depth + 1,
            )


    def blast_radius(
        self,
        asset_id,
        depth=5,
    ):
        """
        Calculate the downstream blast radius of an asset.

        The registry may expose a logical asset ID while the topology
        graph stores a canonical discovered ID. Resolve the identity
        first and then traverse downstream dependencies.

        Returned items are compatible with RootCauseEngine:
            asset
            via
            depth
            confidence
            evidence
            relationship_weight
            impact_score
        """

        resolved_asset_id = self._resolve_graph_asset_id(
            asset_id
        )

        if resolved_asset_id != asset_id:
            print(
                "BLAST RADIUS ID RESOLVED:",
                asset_id,
                "->",
                resolved_asset_id,
            )

        visited = {resolved_asset_id}
        result = []

        self._walk_blast_radius(
            resolved_asset_id,
            visited,
            result,
            depth,
            current_depth=1,
        )

        return result


    def _walk_blast_radius(
        self,
        asset_id,
        visited,
        result,
        depth,
        current_depth=1,
    ):
        if depth <= 0:
            return

        for rel in self.graph.get_children(asset_id):

            target = rel["target"]

            if target in visited:
                continue

            visited.add(target)

            relationship = rel.get(
                "type",
                "UNKNOWN",
            )

            try:
                relationship_type = RelationshipType[
                    relationship
                ]

                weight = relationship_impact_score(
                    relationship_type
                )

            except (KeyError, TypeError):
                weight = 1

            confidence = float(
                rel.get(
                    "confidence",
                    0.0,
                )
                or 0.0
            )

            impact_score = (
                float(weight)
                * confidence
                / current_depth
            )

            result.append(
                {
                    "asset": target,
                    "via": relationship,
                    "depth": current_depth,
                    "confidence": confidence,
                    "evidence": rel.get(
                        "evidence",
                        [],
                    ),
                    "relationship_weight": weight,
                    "impact_score": impact_score,
                }
            )

            self._walk_blast_radius(
                target,
                visited,
                result,
                depth - 1,
                current_depth + 1,
            )
    def impact_analysis(
        self,
        asset_id,
        depth=5,
    ):
        """
        Compatibility API for historical GraphService callers.

        Canonical downstream impact traversal is implemented by
        blast_radius(). Upstream operational traversal is exposed
        separately through critical_upstream().
        """

        return self.blast_radius(
            asset_id,
            depth=depth,
        )


    def critical_upstream(
        self,
        asset_id,
        depth=5,
    ):
        """
        Return the complete operational upstream dependency chain.
        """

        resolved_asset_id = self._resolve_graph_asset_id(
            asset_id
        )

        if resolved_asset_id != asset_id:
            print(
                "CRITICAL UPSTREAM ID RESOLVED:",
                asset_id,
                "->",
                resolved_asset_id,
            )

        visited = set()
        result = []

        self._walk_operational_up(
            resolved_asset_id,
            visited,
            result,
            depth,
        )

        return result

    def operational_upstream(
        self,
        asset_id,
        depth=5,
    ):
        """
        Return operationally relevant upstream infrastructure.

        This is the public semantic API for operational upstream
        traversal. The canonical traversal implementation remains
        critical_upstream(), so scoring and metadata stay centralized.
        """

        return self.critical_upstream(
            asset_id,
            depth=depth,
        )


    def _walk_operational_up(
        self,
        asset_id,
        visited,
        result,
        depth,
        current_depth=1,
    ):
        """
        Walk upstream operational infrastructure while preserving
        traversal metadata.
        """

        if depth <= 0:
            return

        for rel in self.graph.get_parents(asset_id):

            try:
                relationship_type = RelationshipType[
                    rel["type"]
                ]
            except (KeyError, TypeError):
                continue

            if not is_operational_relationship(
                relationship_type
            ):
                continue

            source = rel["source"]

            if source in visited:
                continue

            if self._is_system_service(source):
                continue

            visited.add(source)

            weight = relationship_impact_score(
                relationship_type
            )

            confidence = float(
                rel.get(
                    "confidence",
                    1.0,
                )
                or 0.0
            )

            evidence = list(
                rel.get(
                    "evidence",
                    [],
                )
                or []
            )

            impact_score = (
                float(weight)
                * confidence
                / current_depth
            )

            result.append(
                {
                    "asset_id": source,
                    "relationship": rel["type"],
                    "direction": "UPSTREAM",
                    "depth": current_depth,
                    "confidence": confidence,
                    "evidence": evidence,
                    "relationship_weight": weight,
                    "impact_score": impact_score,
                }
            )

            self._walk_operational_up(
                source,
                visited,
                result,
                depth - 1,
                current_depth + 1,
            )
