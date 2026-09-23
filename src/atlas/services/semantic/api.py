from __future__ import annotations

from typing import Any

from atlas.core.asset import (
    AssetRole,
    AssetStatus,
    AssetType,
    Criticality,
)

from atlas.services.assets.runtime import get_asset_registry
from atlas.services.assets.registry import AssetRegistry
from atlas.services.assets.context_builder import AssetContextBuilder
from atlas.services.assets.context_service import AssetContextService
from atlas.services.assets.topology_traversal import TopologyTraversalService
from atlas.services.knowledge.asset_resolver import AssetResolver
from atlas.services.noc.impact import ImpactEngine
from atlas.services.semantic.attention import (
    OperationalAttentionService,
)
from atlas.services.semantic.entity_resolver import (
    SemanticEntityResolver,
)
from atlas.services.semantic.graph_query import (
    SemanticGraphQueryService,
)


class AtlasSemanticAPI:
    """
    Canonical read-only semantic interface for ATLAS.

    This layer intentionally hides repositories and infrastructure
    implementation details from consumers such as MCP and the LLM.

    Semantic flow:

        user intent
            ->
        semantic operation
            ->
        AssetRegistry / Knowledge / Graph / Telemetry
            ->
        structured infrastructure facts
    """

    def __init__(
        self,
        registry: AssetRegistry | None = None,
        attention_service=None,
    ) -> None:

        self.registry = (
            registry
            or get_asset_registry()
        )

        self.resolver = AssetResolver(
            self.registry
        )

        self.entity_resolver = (
            SemanticEntityResolver(
                self.registry,
                asset_resolver=self.resolver,
            )
        )

        self._semantic_graph = (
            SemanticGraphQueryService(
                self.registry,
                entity_resolver=self.entity_resolver,
            )
        )

        # Traversal service is kept private so it does not
        # collide with the public semantic `topology()` method.
        self._topology = TopologyTraversalService(
            registry=self.registry
        )

        self._attention = (
            attention_service
            or OperationalAttentionService()
        )



    # ------------------------------------------------------------------
    # SEMANTIC ENTITY
    # ------------------------------------------------------------------

    def resolve_entity(
        self,
        query: str,
    ) -> dict[str, Any]:
        """
        Resolve a human-readable concept to a canonical semantic entity.

        The result may represent one asset, a discovered logical group,
        an ambiguous entity or a missing entity.
        """

        entity = (
            self.entity_resolver
            .resolve(
                query
            )
        )

        return {
            "status": (
                "SUCCESS"
                if entity.resolved
                else entity.kind.value
            ),
            "entity":
                entity.as_dict(),
        }


    def entity_relations(
        self,
        entity_query: str,
        *,
        relationship=None,
        direction="downstream",
        depth=1,
    ) -> dict[str, Any]:
        """
        Traverse relationships for an asset or semantic group.

        GROUP queries are expanded internally by the semantic graph
        service, so consumers do not need to iterate group members.
        """

        return (
            self._semantic_graph
            .query(
                entity_query,
                relationship=relationship,
                orientation=direction,
                depth=depth,
            )
        )


    # ------------------------------------------------------------------
    # OPERATIONAL ATTENTION
    # ------------------------------------------------------------------

    def attention(
        self,
    ) -> dict[str, Any]:
        """
        Return current operational signals that require attention.

        This is a semantic capability, not a natural-language rule.
        """

        return {
            "status":
                "SUCCESS",

            "attention":
                self._attention.summary(),
        }

    # ------------------------------------------------------------------
    # FIND
    # ------------------------------------------------------------------

    def find(
        self,
        query: str,
    ) -> dict[str, Any]:

        if not query or not query.strip():
            return {
                "status": "ERROR",
                "error": "query is required",
                "matches": [],
            }

        normalized = query.strip().lower()
        matches = []

        for asset in self.registry.assets():

            haystack = [
                asset.id,
                asset.name,
                getattr(asset.identity, "serial", None),
                getattr(asset.identity, "model", None),
                getattr(asset.identity, "vendor", None),
                getattr(asset.identity, "device", None),
            ]

            metadata = getattr(
                asset,
                "metadata",
                {},
            ) or {}

            haystack.extend(
                str(value)
                for value in metadata.values()
                if value is not None
            )

            roles = [
                role.name
                for role in getattr(
                    asset,
                    "asset_roles",
                    set(),
                )
            ]

            haystack.extend(roles)

            if any(
                normalized in str(value).lower()
                for value in haystack
                if value is not None
            ):
                matches.append(
                    self._asset_summary(asset)
                )

        return {
            "status": "SUCCESS",
            "query": query,
            "count": len(matches),
            "matches": matches,
        }

    # ------------------------------------------------------------------
    # ASSET
    # ------------------------------------------------------------------

    def asset(
        self,
        asset_id: str,
    ) -> dict[str, Any]:

        if not asset_id:
            return {
                "status": "ERROR",
                "error": "asset_id is required",
            }

        resolved = self._resolve(asset_id)

        if resolved is None:
            return {
                "status": "NOT_FOUND",
                "error": f"Asset not found: {asset_id}",
            }

        context_service = AssetContextService(
            AssetContextBuilder(
                self.registry
            )
        )

        context = context_service.get(
            resolved.id
        )

        result = self._asset_summary(
            resolved
        )

        result["identity"] = {
            "serial": resolved.identity.serial,
            "model": resolved.identity.model,
            "vendor": resolved.identity.vendor,
            "firmware": resolved.identity.firmware,
            "device": resolved.identity.device,
        }

        result["metadata"] = dict(
            resolved.metadata or {}
        )

        result["capabilities"] = [
            capability.name
            for capability in resolved.capabilities
        ]

        result["observations"] = [
            {
                "type": observation.type,
                "value": observation.value,
                "severity": observation.severity,
                "source": observation.source,
                "timestamp": observation.timestamp.isoformat(),
            }
            for observation in resolved.observations
        ]

        if context is not None:
            result["topology"] = {
                "parents": context.parents,
                "children": context.children,
            }

        return {
            "status": "SUCCESS",
            "asset": result,
        }

    # ------------------------------------------------------------------
    # ASSETS
    # ------------------------------------------------------------------

    def assets(
        self,
        *,
        query: str | None = None,
        status: str | None = None,
        asset_type: str | None = None,
        criticality: str | None = None,
        role: str | None = None,
    ) -> dict[str, Any]:

        normalized_query = (
            query.strip().lower()
            if query
            else None
        )

        normalized_status = (
            status.strip().upper()
            if status
            else None
        )

        normalized_type = (
            asset_type.strip().upper()
            if asset_type
            else None
        )

        normalized_criticality = (
            criticality.strip().upper()
            if criticality
            else None
        )

        normalized_role = (
            role.strip().upper()
            if role
            else None
        )

        result = []

        for asset in self.registry.assets():

            if normalized_status:
                if asset.status.name != normalized_status:
                    continue

            if normalized_type:
                if asset.type.name != normalized_type:
                    continue

            if normalized_criticality:
                if asset.criticality.name != normalized_criticality:
                    continue

            if normalized_role:
                roles = {
                    item.name
                    for item in asset.asset_roles
                }

                if normalized_role not in roles:
                    continue

            if normalized_query:

                searchable = " ".join(
                    str(value)
                    for value in (
                        asset.id,
                        asset.name,
                        asset.identity.serial,
                        asset.identity.model,
                        asset.identity.vendor,
                        asset.identity.device,
                    )
                    if value
                ).lower()

                if normalized_query not in searchable:
                    continue

            result.append(
                self._asset_summary(asset)
            )

        return {
            "status": "SUCCESS",
            "count": len(result),
            "filters": {
                "query": query,
                "status": status,
                "asset_type": asset_type,
                "criticality": criticality,
                "role": role,
            },
            "assets": result,
        }

    # ------------------------------------------------------------------
    # ASSET STATUS QUERY
    # ------------------------------------------------------------------

    def query_asset_status(
        self,
        *,
        status: str | None = None,
        asset_type: str | None = None,
        criticality: str | None = None,
        role: str | None = None,
    ) -> dict[str, Any]:
        """
        Query current canonical asset status through structured ATLAS
        inventory dimensions.

        This method contains no natural-language parsing.

        All supplied selector values must exist in the canonical ATLAS
        asset ontology. An invalid selector is an error, never an empty
        successful result.

        A successful zero-count result is complete verified evidence that
        no currently registered asset matches the supplied selectors.
        """

        raw_filters = {
            "status": status,
            "asset_type": asset_type,
            "criticality": criticality,
            "role": role,
        }

        enum_contracts = {
            "status": AssetStatus,
            "asset_type": AssetType,
            "criticality": Criticality,
            "role": AssetRole,
        }

        normalized = {}

        for (
            field_name,
            enum_type,
        ) in enum_contracts.items():

            value = raw_filters[
                field_name
            ]

            if value is None:
                continue

            canonical = str(
                value
            ).strip().upper()

            if not canonical:

                return {
                    "status": "ERROR",
                    "error": (
                        f"{field_name} must not be empty"
                    ),
                    "complete": False,
                    "count": 0,
                    "filters": {},
                    "assets": [],
                }

            if (
                canonical
                not in enum_type.__members__
            ):

                return {
                    "status": "ERROR",
                    "error": (
                        f"Unsupported {field_name}: "
                        f"{canonical}"
                    ),
                    "complete": False,
                    "count": 0,
                    "filters": {
                        field_name:
                            canonical,
                    },
                    "assets": [],
                }

            normalized[
                field_name
            ] = canonical

        result = self.assets(
            status=normalized.get(
                "status"
            ),
            asset_type=normalized.get(
                "asset_type"
            ),
            criticality=normalized.get(
                "criticality"
            ),
            role=normalized.get(
                "role"
            ),
        )

        if (
            result.get(
                "status"
            )
            != "SUCCESS"
        ):

            return {
                "status": "ERROR",
                "error": (
                    result.get(
                        "error"
                    )
                    or "Asset inventory query failed"
                ),
                "complete": False,
                "count": 0,
                "filters": normalized,
                "assets": [],
            }

        assets = list(
            result.get(
                "assets",
                [],
            )
            or []
        )

        return {
            "status": "SUCCESS",
            "complete": True,
            "count": len(
                assets
            ),
            "filters": {
                "status":
                    normalized.get(
                        "status"
                    ),

                "asset_type":
                    normalized.get(
                        "asset_type"
                    ),

                "criticality":
                    normalized.get(
                        "criticality"
                    ),

                "role":
                    normalized.get(
                        "role"
                    ),
            },
            "assets": assets,
            "evidence": [
                (
                    "complete query over current "
                    "ATLAS AssetRegistry"
                ),
                (
                    f"{len(assets)} assets matched "
                    "canonical status selectors"
                ),
            ],
        }


    # ------------------------------------------------------------------
    # INFRASTRUCTURE
    # ------------------------------------------------------------------

    def infrastructure(self) -> dict[str, Any]:

        assets = self.registry.assets()

        groups: dict[str, list] = {
            "servers": [],
            "vms": [],
            "lxcs": [],
            "containers": [],
            "applications": [],
            "databases": [],
            "storage": [],
            "network": [],
            "sensors": [],
            "services": [],
        }

        for asset in assets:

            mapping = {
                "SERVER": "servers",
                "VM": "vms",
                "LXC": "lxcs",
                "CONTAINER": "containers",
                "APPLICATION": "applications",
                "DATABASE": "databases",
                "STORAGE": "storage",
                "NETWORK": "network",
                "SENSOR": "sensors",
                "SERVICE": "services",
            }

            key = mapping.get(
                asset.type.name
            )

            if key:
                groups[key].append(
                    self._asset_summary(asset)
                )

        return {
            "status": "SUCCESS",
            "total_assets": len(assets),
            "inventory": groups,
        }

    # ------------------------------------------------------------------
    # TOPOLOGY
    # ------------------------------------------------------------------

    def topology(
        self,
        asset_id: str,
        direction: str = "neighbors",
        depth: int = 5,
    ) -> dict[str, Any]:

        if not asset_id:
            return {
                "status": "ERROR",
                "error": "asset_id is required",
            }

        resolved = self._resolve(
            asset_id
        )

        if resolved is None:
            return {
                "status": "NOT_FOUND",
                "error": f"Asset not found: {asset_id}",
            }

        direction = (
            direction or "neighbors"
        ).strip().lower()

        depth = max(
            1,
            min(int(depth), 20),
        )

        if direction == "upstream":
            result = self._topology.upstream(
                resolved.id,
                depth=depth,
            )

        elif direction == "downstream":
            result = self._topology.downstream(
                resolved.id,
                depth=depth,
            )

        elif direction == "critical_upstream":
            result = self._topology.critical_upstream(
                resolved.id,
                depth=depth,
            )

        elif direction == "operational_upstream":
            result = self._topology.operational_upstream(
                resolved.id,
                depth=depth,
            )

        elif direction == "blast_radius":
            result = self._topology.blast_radius(
                resolved.id,
                depth=depth,
            )

        elif direction == "impact":
            result = self._topology.impact_analysis(
                resolved.id,
                depth=depth,
            )

        elif direction == "neighbors":

            upstream = self._topology.upstream(
                resolved.id,
                depth=depth,
            )

            downstream = self._topology.downstream(
                resolved.id,
                depth=depth,
            )

            # Preserve canonical direction metadata emitted by
            # TopologyTraversalService while preventing exact
            # duplicate rows in the combined neighborhood.
            result = []
            seen = set()

            for item in (
                list(upstream)
                + list(downstream)
            ):

                if isinstance(
                    item,
                    dict,
                ):

                    key = (
                        item.get(
                            "asset_id"
                        ),
                        item.get(
                            "relationship"
                        ),
                        item.get(
                            "direction"
                        ),
                        item.get(
                            "depth"
                        ),
                    )

                else:

                    key = repr(
                        item
                    )

                if key in seen:
                    continue

                seen.add(
                    key
                )

                result.append(
                    item
                )

        elif direction == "dependencies":

            result = [
                item
                for item in self._topology.downstream(
                    resolved.id,
                    depth=depth,
                )
                if (
                    isinstance(
                        item,
                        dict,
                    )
                    and str(
                        item.get(
                            "relationship",
                            ""
                        )
                        or ""
                    ).strip().upper()
                    == "DEPENDS_ON"
                )
            ]

        elif direction == "dependents":

            result = [
                item
                for item in self._topology.upstream(
                    resolved.id,
                    depth=depth,
                )
                if (
                    isinstance(
                        item,
                        dict,
                    )
                    and str(
                        item.get(
                            "relationship",
                            ""
                        )
                        or ""
                    ).strip().upper()
                    == "DEPENDS_ON"
                )
            ]

        else:
            return {
                "status": "ERROR",
                "error": (
                    f"Unsupported topology direction: "
                    f"{direction}"
                ),
            }

        return {
            "status": "SUCCESS",
            "asset": self._asset_summary(
                resolved
            ),
            "direction": direction,
            "depth": depth,
            "results": result,
        }

    # ------------------------------------------------------------------
    # IMPACT
    # ------------------------------------------------------------------

    def impact(
        self,
        asset_id: str,
        depth: int = 5,
    ) -> dict[str, Any]:

        if not asset_id:
            return {
                "status": "ERROR",
                "error": "asset_id is required",
            }

        resolved = self._resolve(
            asset_id
        )

        if resolved is None:
            return {
                "status": "NOT_FOUND",
                "error": f"Asset not found: {asset_id}",
            }

        engine = ImpactEngine()

        result = engine.analyze(
            resolved.id
        )

        if not result:
            result = {}

        return {
            "status": "SUCCESS",
            "asset": self._asset_summary(
                resolved
            ),
            "depth": depth,
            "impact": result,
        }

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _resolve(
        self,
        value: str,
    ):
        """
        Resolve an infrastructure entity through the canonical
        AssetResolver.

        Resolution priority is intentionally deterministic:

        1. exact asset id
        2. exact asset name
        3. identity / metadata
        4. partial matching

        AssetResolver is the single semantic resolution authority.
        """

        if not value or not value.strip():
            return None

        value = value.strip()

        # Canonical resolver.
        asset = self.resolver.get(value)

        if asset is not None:
            return asset

        # Dependency-aware semantic resolution.
        asset = self.resolver.resolve_dependency(value)

        if asset is not None:
            return asset

        return None

    def _asset_summary(
        self,
        asset,
    ) -> dict[str, Any]:

        if asset is None:
            return {}

        identity = getattr(
            asset,
            "identity",
            None,
        )

        roles = getattr(
            asset,
            "asset_roles",
            set(),
        ) or set()

        capabilities = getattr(
            asset,
            "capabilities",
            set(),
        ) or set()

        return {
            "id": getattr(
                asset,
                "id",
                None,
            ),

            "name": getattr(
                asset,
                "name",
                None,
            ),

            "type": getattr(
                getattr(
                    asset,
                    "type",
                    None,
                ),
                "name",
                "UNKNOWN",
            ),

            "status": getattr(
                getattr(
                    asset,
                    "status",
                    None,
                ),
                "name",
                "UNKNOWN",
            ),

            "health": getattr(
                asset,
                "health",
                None,
            ),

            "criticality": getattr(
                getattr(
                    asset,
                    "criticality",
                    None,
                ),
                "name",
                "UNKNOWN",
            ),

            "roles": [
                getattr(
                    role,
                    "name",
                    str(role),
                )
                for role in roles
            ],

            "capabilities": [
                getattr(
                    capability,
                    "name",
                    str(capability),
                )
                for capability in capabilities
            ],

            "last_seen": (
                asset.last_seen.isoformat()
                if getattr(
                    asset,
                    "last_seen",
                    None,
                )
                else None
            ),

            "identity": {
                "serial": getattr(
                    identity,
                    "serial",
                    None,
                ),
                "model": getattr(
                    identity,
                    "model",
                    None,
                ),
                "vendor": getattr(
                    identity,
                    "vendor",
                    None,
                ),
                "firmware": getattr(
                    identity,
                    "firmware",
                    None,
                ),
                "device": getattr(
                    identity,
                    "device",
                    None,
                ),
            },

            "metadata": dict(
                getattr(
                    asset,
                    "metadata",
                    {},
                )
                or {}
            ),
        }
