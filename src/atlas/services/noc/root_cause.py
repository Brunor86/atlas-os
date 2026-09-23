import logging

from atlas.core.asset import (
    AssetRole,
    AssetType,
    ServiceRole,
)


logger = logging.getLogger(__name__)


def _diagnostic(*parts):

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


class RootCauseEngine:


    def __init__(
        self,
        knowledge=None,
        graph=None,
    ):

        self.knowledge = knowledge

        self.graph = graph


    def _registry(self):
        """
        Return the best available runtime asset registry.
        """

        if self.graph is not None:

            topology = getattr(
                self.graph,
                "topology",
                None,
            )

            registry = getattr(
                topology,
                "assets",
                None,
            )

            if registry is not None:
                return registry

        if self.knowledge is not None:

            registry = getattr(
                self.knowledge,
                "registry",
                None,
            )

            if registry is not None:
                return registry

        return None


    def _all_assets(
        self,
        assets=None,
    ):
        """
        Yield unique assets from the explicit context and runtime
        registry without depending on identifier conventions.
        """

        result = []
        seen = set()

        for asset in assets or []:

            asset_id = str(
                getattr(
                    asset,
                    "id",
                    "",
                )
            )

            if asset_id in seen:
                continue

            seen.add(
                asset_id
            )

            result.append(
                asset
            )

        registry = self._registry()

        if registry is None:
            return result

        try:
            discovered = (
                registry.get_all_assets()
            )
        except Exception:

            try:
                discovered = (
                    registry.assets()
                )
            except Exception:
                discovered = []

        for asset in discovered or []:

            asset_id = str(
                getattr(
                    asset,
                    "id",
                    "",
                )
            )

            if asset_id in seen:
                continue

            seen.add(
                asset_id
            )

            result.append(
                asset
            )

        return result


    def _resolve_asset(
        self,
        asset_id,
        assets=None,
    ):
        """
        Resolve an event/topology identifier to its canonical Asset.

        Historical ``container-*`` IDs are resolved by workload name
        against Docker-discovered APPLICATION assets. Product names
        are never known by this layer.
        """

        if not asset_id:
            return None

        asset_id = str(
            asset_id
        )

        # ------------------------------------------------------------
        # Direct lookup in explicitly supplied assets.
        # ------------------------------------------------------------

        for asset in assets or []:

            if str(
                getattr(
                    asset,
                    "id",
                    "",
                )
            ) == asset_id:
                return asset

        # ------------------------------------------------------------
        # Direct registry lookup.
        # ------------------------------------------------------------

        registry = self._registry()

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
                    asset = method(
                        asset_id
                    )
                except Exception:
                    asset = None

                if asset is not None:
                    return asset

        # ------------------------------------------------------------
        # Historical Docker event namespace.
        #
        # This is protocol compatibility, not application knowledge.
        # ------------------------------------------------------------

        if not asset_id.startswith(
            "container-"
        ):
            return None

        workload_name = (
            asset_id[
                len("container-"):
            ]
            .strip()
            .lower()
        )

        if not workload_name:
            return None

        for candidate in self._all_assets(
            assets
        ):

            if (
                getattr(
                    candidate,
                    "type",
                    None,
                )
                != AssetType.APPLICATION
            ):
                continue

            metadata = (
                getattr(
                    candidate,
                    "metadata",
                    None,
                )
                or {}
            )

            if str(
                metadata.get(
                    "runtime",
                    "",
                )
            ).lower() != "docker":
                continue

            candidate_name = str(
                getattr(
                    candidate,
                    "name",
                    "",
                )
            ).strip().lower()

            if candidate_name == workload_name:
                return candidate

        return None


    @staticmethod
    def _is_container_runtime_asset(
        asset,
    ):
        """
        Classify assets using domain semantics rather than names.
        """

        if asset is None:
            return False

        metadata = (
            getattr(
                asset,
                "metadata",
                None,
            )
            or {}
        )

        asset_type = getattr(
            asset,
            "type",
            None,
        )

        if (
            asset_type == AssetType.APPLICATION
            and str(
                metadata.get(
                    "runtime",
                    "",
                )
            ).lower() == "docker"
        ):
            return True

        roles = (
            getattr(
                asset,
                "asset_roles",
                None,
            )
            or set()
        )

        if AssetRole.DOCKER_HOST in roles:
            return True

        if (
            asset_type == AssetType.SERVICE
            and getattr(
                asset,
                "service_role",
                None,
            )
            == ServiceRole.CONTAINER_RUNTIME
        ):
            return True

        return False


    def resolve_impact(
        self,
        asset_id,
    ):
        """
        Resolve the operational impact of an asset failure.

        Impact is composed of:
        - downstream affected assets
        - upstream supporting infrastructure

        For application assets, upstream infrastructure is especially
        important because a leaf application may have no downstream
        children while still depending on a Docker host, VM, or
        hypervisor.
        """

        if not self.graph:
            return []

        # ---------------------------------------------------------
        # Canonicalize event identifiers before graph traversal.
        # ---------------------------------------------------------

        original_asset_id = asset_id

        resolved_asset = self._resolve_asset(
            asset_id
        )

        if resolved_asset is not None:

            asset_id = str(
                resolved_asset.id
            )

            if asset_id != original_asset_id:

                _diagnostic(
                    "DEBUG ASSET RESOLVED:",
                    original_asset_id,
                    "->",
                    asset_id,
                )

        try:
            _diagnostic(
                "GRAPH IMPACT CHECK:",
                asset_id,
            )

            # ---------------------------------------------------------
            # 1. Resolve downstream blast radius
            # ---------------------------------------------------------

            blast = self.graph.blast_radius(
                asset_id
            )

            relevant = []

            for item in blast:

                target = item.get(
                    "asset",
                    "",
                )

                asset = self._resolve_asset(
                    target
                )

                if asset is None:
                    _diagnostic(
                        "DEBUG IMPACT ASSET NOT RESOLVED:",
                        target,
                    )
                    continue

                # System services are implementation detail unless
                # they represent the container runtime itself.
                if (
                    asset.type == AssetType.SERVICE
                    and asset.service_role
                    != ServiceRole.CONTAINER_RUNTIME
                ):
                    continue

                try:
                    criticality = asset.criticality.name
                except Exception:
                    criticality = "UNKNOWN"

                try:
                    roles = [
                        role.name
                        for role in asset.asset_roles
                    ]
                except Exception:
                    roles = []

                try:
                    role_weight = asset.role_weight()
                except Exception:
                    role_weight = 0

                try:
                    importance = asset.service_importance.name
                except Exception:
                    importance = "UNKNOWN"

                try:
                    asset_type = asset.type.name
                except Exception:
                    asset_type = "UNKNOWN"

                relevant.append(
                    {
                        "asset_id": target,
                        "application": target,
                        "name": asset.name,
                        "type": asset_type,
                        "impact_class": "DOWNSTREAM",
                        "criticality": criticality,
                        "roles": roles,
                        "role_weight": role_weight,
                        "importance": importance,
                        "depth": item.get(
                            "depth",
                            0,
                        ),
                        "confidence": item.get(
                            "confidence",
                            0.0,
                        ),
                        "evidence": item.get(
                            "evidence",
                            [],
                        ),
                        "relationship_weight": item.get(
                            "relationship_weight",
                            0,
                        ),
                        "impact_score": item.get(
                            "impact_score",
                            0.0,
                        ),
                        "reason": (
                            f"Downstream impact through "
                            f"{item.get('via', 'UNKNOWN')}"
                        ),
                    }
                )

            # ---------------------------------------------------------
            # 2. Resolve upstream supporting infrastructure
            # ---------------------------------------------------------

            upstream = self.graph.operational_upstream(
            asset_id
        )

            for item in upstream:

                target = item.get(
                    "asset_id",
                    "",
                )

                if not target:
                    continue

                asset = self.graph.topology.assets.get_asset(
                    target
                )

                if asset is None:
                    _diagnostic(
                        "DEBUG UPSTREAM ASSET NOT RESOLVED:",
                        target,
                    )
                    continue

                try:
                    criticality = asset.criticality.name
                except Exception:
                    criticality = "UNKNOWN"

                try:
                    roles = [
                        role.name
                        for role in asset.asset_roles
                    ]
                except Exception:
                    roles = []

                try:
                    role_weight = asset.role_weight()
                except Exception:
                    role_weight = 0

                try:
                    importance = asset.service_importance.name
                except Exception:
                    importance = "UNKNOWN"

                try:
                    asset_type = asset.type.name
                except Exception:
                    asset_type = "UNKNOWN"

                # Hosting infrastructure has a different semantic
                # meaning from downstream application impact.
                if (
                    "DOCKER_HOST" in roles
                    or "HYPERVISOR" in roles
                    or asset_type in {
                        "SERVER",
                        "VM",
                        "LXC",
                    }
                ):
                    impact_class = "INFRASTRUCTURE"
                else:
                    impact_class = "UPSTREAM"

                relevant.append(
                    {
                        "asset_id": target,
                        "application": asset.name,
                        "name": asset.name,
                        "type": asset_type,
                        "impact_class": impact_class,
                        "criticality": criticality,
                        "roles": roles,
                        "role_weight": role_weight,
                        "importance": importance,
                        "depth": item.get(
                            "depth",
                            0,
                        ),
                        "confidence": float(
                            item.get(
                                "confidence",
                                0.0,
                            )
                            or 0.0
                        ),
                        "evidence": list(
                            item.get(
                                "evidence",
                                [],
                            )
                            or []
                        ),
                        "relationship_weight": item.get(
                            "weight",
                            item.get(
                                "relationship_weight",
                                0,
                            ),
                        ),
                        "impact_score": float(
                            item.get(
                                "impact_score",
                                0.0,
                            )
                            or 0.0
                        ),
                        "reason": (
                            f"Supporting infrastructure through "
                            f"{item.get('relationship', 'UNKNOWN')}"
                        ),
                    }
                )

            # ---------------------------------------------------------
            # 3. Deduplicate assets
            # ---------------------------------------------------------

            deduplicated = {}

            for item in relevant:
                asset_key = item["asset_id"]

                existing = deduplicated.get(
                    asset_key
                )

                if existing is None:
                    deduplicated[asset_key] = item
                    continue

                # Keep the strongest impact representation.
                if (
                    item.get("impact_score", 0)
                    > existing.get("impact_score", 0)
                ):
                    deduplicated[asset_key] = item

            return list(
                deduplicated.values()
            )

        except Exception as e:

            _diagnostic(
                "IMPACT ERROR:",
                type(e).__name__,
                str(e),
            )

            return []


    def calculate_role_severity(
        self,
        assets,
    ):
        """Calculate severity from resolved impact metadata."""

        if not assets:
            return "LOW"

        role_weights = []
        impact_scores = []

        for item in assets:

            if not isinstance(item, dict):
                continue

            try:
                role_weight = float(
                    item.get(
                        "role_weight",
                        0,
                    )
                    or 0
                )

                impact_score = float(
                    item.get(
                        "impact_score",
                        0.0,
                    )
                    or 0.0
                )

            except (TypeError, ValueError):
                continue

            if role_weight > 0:
                role_weights.append(
                    role_weight
                )

            if impact_score > 0:
                impact_scores.append(
                    impact_score
                )

        if not impact_scores:
            return "LOW"

        highest_role_weight = (
            max(role_weights)
            if role_weights
            else 0.0
        )

        average_role_weight = (
            sum(role_weights)
            / len(role_weights)
            if role_weights
            else 0.0
        )

        highest_impact = max(
            impact_scores
        )

        average_impact = (
            sum(impact_scores)
            / len(impact_scores)
        )

        if (
            highest_impact >= 95
            or (
                highest_role_weight >= 90
                and average_impact >= 75
            )
        ):
            return "CRITICAL"

        if (
            highest_impact >= 80
            or highest_role_weight >= 80
            or average_impact >= 60
        ):
            return "HIGH"

        if (
            highest_impact >= 50
            or average_impact >= 40
            or average_role_weight >= 40
        ):
            return "MEDIUM"

        return "LOW"


    def analyze(
            self,
            events=None,
            logs=None,
            health=None,
            assets=None,
        ):


            incidents = []


            events = events or []

            logs = logs or []

            _diagnostic("ANALYZE 2 EVENTS:", len(events))
            _diagnostic("ANALYZE 2 ASSETS:", len(assets or []))



            has_container_event = False


            event_details = []



            _diagnostic("ANALYZE 3 BEFORE EVENTS")

            for event in events:


                asset_id = None


                if isinstance(event, dict):

                    title = event.get(
                        "title",
                        "",
                    )

                    message = event.get(
                        "message",
                        event.get(
                            "detail",
                            "",
                        ),
                    )

                    asset_id = event.get(
                        "asset_id"
                    )

                else:

                    title = getattr(
                        event,
                        "title",
                        "",
                    )


                    message = getattr(
                        event,
                        "message",
                        "",
                    )


                    asset_id = getattr(
                        event,
                        "asset_id",
                        None,
                    )



                resolved_asset = self._resolve_asset(
                    asset_id,
                    assets,
                )

                canonical_asset_id = (
                    str(
                        resolved_asset.id
                    )
                    if resolved_asset is not None
                    else asset_id
                )

                # Event semantics come from the referenced asset.
                # The container-* namespace is retained only as
                # backwards compatibility for historical events.
                is_runtime_event = (
                    self._is_container_runtime_asset(
                        resolved_asset
                    )
                    or (
                        resolved_asset is None
                        and isinstance(
                            asset_id,
                            str,
                        )
                        and asset_id.startswith(
                            "container-"
                        )
                    )
                )

                if is_runtime_event:

                    has_container_event = True

                    event_details.append(
                        {
                            "title": title,
                            "detail": message,
                            "asset_id":
                                canonical_asset_id,
                        }
                    )




            repeated_exception = False


            log_details = []



            for item in logs:


                if item.get(
                    "pattern"
                ) == "repeated_exception":


                    repeated_exception = True


                    log_details.append(

                        {
                            "title":
                                "Log analysis",

                            "detail":
                                item.get(
                                    "message",
                                    ""
                                ),

                        }

                    )




            degraded = False



            if health:


                if isinstance(
                    health,
                    dict
                ):

                    status = health.get(
                        "status",
                        "",
                    )

                else:

                    status = getattr(
                        health,
                        "status",
                        "",
                    )


                degraded = (

                    status.lower()
                    ==
                    "degraded"

                )



            health_details = []



            if degraded:


                health_details.append(

                    {
                        "title":
                            "Health",

                        "detail":
                            "Infrastructure health degraded",

                    }

                )



            asset_candidates = [
                detail.get("asset_id")
                for detail in event_details
                if detail.get("asset_id")
            ]


            role_assets = []


            role_asset_ids = set(
                asset_candidates
            )


            #
            # Include infrastructure impact
            #

            for asset_id in asset_candidates:

                impacts = self.resolve_impact(
                    asset_id
                )


                for item in impacts:

                    role_asset_ids.add(
                        item["asset_id"]
                    )



            for asset_id in role_asset_ids:

                asset = next(
                    (
                        a
                        for a in (assets or [])
                        if a.id == asset_id
                    ),
                    None,
                )

                # Fallback: cuando analyze() recibe assets=[],
                # resolver directamente desde el registry de KnowledgeService.
                if asset is None and self.knowledge is not None:

                    registry = getattr(
                        self.knowledge,
                        "registry",
                        None,
                    )

                    if registry is not None:

                        try:
                            asset = registry.get(
                                asset_id
                            )
                        except Exception:
                            asset = None

                if asset:

                    role_assets.append(
                        asset
                    )



            role_severity = (
                self.calculate_role_severity(
                    role_assets
                )
            )



            confidence = 0


            evidence = []



            if has_container_event:


                confidence += 0.35


                evidence.extend(
                    event_details
                )



            if repeated_exception:


                confidence += 0.45


                evidence.extend(
                    log_details
                )



            if degraded:


                confidence += 0.20


                evidence.extend(
                    health_details
                )




            _diagnostic("ANALYZE 4 CONFIDENCE:", confidence)

            if confidence >= 0.3:


                severity = role_severity or "MEDIUM"


                _diagnostic("ANALYZE 5 BEFORE AFFECTED")

                affected_assets = []

                for detail in event_details:

                    candidate = detail.get(
                        "asset_id",
                        "unknown",
                    )

                    if candidate != "unknown":

                        affected_assets.append(
                            candidate
                        )
                # ---------------------------------------------------------
                # Resolve Docker root cause
                # ---------------------------------------------------------
                #
                # Historical Docker events use container-* identifiers,
                # while the Asset Registry stores Docker workloads as
                # application-* assets.
                #
                # Multiple Docker workload failures represent a Docker
                # service/runtime incident, not an unknown root cause.
                #

                runtime_event_assets = []

                for candidate in asset_candidates:

                    candidate_asset = (
                        self._resolve_asset(
                            candidate,
                            assets,
                        )
                    )

                    if self._is_container_runtime_asset(
                        candidate_asset
                    ):
                        runtime_event_assets.append(
                            candidate
                        )

                    elif (
                        candidate_asset is None
                        and isinstance(
                            candidate,
                            str,
                        )
                        and candidate.startswith(
                            "container-"
                        )
                    ):
                        runtime_event_assets.append(
                            candidate
                        )

                if runtime_event_assets:

                    # Generic logical root for a container-runtime
                    # incident. This is not tied to any host identity.
                    asset_id = "docker-service"

                elif len(asset_candidates) == 1:

                    asset_id = asset_candidates[0]

                else:

                    asset_id = "unknown"


                supporting_infrastructure = []

                supporting_seen = set()

                for affected in affected_assets:

                    impacts = self.resolve_impact(
                        affected
                    )

                    for item in impacts:

                        key = item.get(
                            "asset_id"
                        )

                        if not key:
                            continue

                        if key in supporting_seen:
                            continue

                        supporting_seen.add(
                            key
                        )

                        supporting_infrastructure.append(
                            {
                                "asset_id":
                                    key,

                                "application":
                                    item.get(
                                        "application",
                                        key,
                                    ),

                                "name":
                                    item.get(
                                        "name",
                                        key,
                                    ),

                                "type":
                                    item.get(
                                        "type",
                                        "UNKNOWN",
                                    ),

                                "importance":
                                    item.get(
                                        "importance",
                                        "UNKNOWN",
                                    ),

                                "criticality":
                                    item.get(
                                        "criticality",
                                        "UNKNOWN",
                                    ),

                                "roles":
                                    item.get(
                                        "roles",
                                        [],
                                    ),

                                "role_weight":
                                    item.get(
                                        "role_weight",
                                        0,
                                    ),

                                "depth":
                                    item.get(
                                        "depth",
                                        0,
                                    ),

                                "confidence":
                                    item.get(
                                        "confidence",
                                        0.0,
                                    ),

                                "evidence":
                                    item.get(
                                        "evidence",
                                        [],
                                    ),

                                "relationship_weight":
                                    item.get(
                                        "relationship_weight",
                                        0,
                                    ),

                                "impact_score":
                                    item.get(
                                        "impact_score",
                                        0.0,
                                    ),

                                "reason":
                                    item.get(
                                        "reason",
                                        "",
                                    ),
                            }
                        )




                blast_radius = []

                blast_seen = set()

                for affected in affected_assets:

                    impacts = self.resolve_impact(
                        affected
                    )

                    for item in impacts:

                        key = item.get(
                            "asset_id"
                        )

                        if not key:
                            continue

                        if key in blast_seen:
                            continue

                        blast_seen.add(
                            key
                        )

                        blast_radius.append(
                            {
                                "asset":
                                    key,

                                "application":
                                    item.get(
                                        "application",
                                        key,
                                    ),

                                "name":
                                    item.get(
                                        "name",
                                        key,
                                    ),

                                "type":
                                    item.get(
                                        "type",
                                        "UNKNOWN",
                                    ),

                                "criticality":
                                    item.get(
                                        "criticality",
                                        "UNKNOWN",
                                    ),

                                "roles":
                                    item.get(
                                        "roles",
                                        [],
                                    ),

                                "role_weight":
                                    item.get(
                                        "role_weight",
                                        0,
                                    ),

                                "importance":
                                    item.get(
                                        "importance",
                                        "UNKNOWN",
                                    ),

                                "depth":
                                    item.get(
                                        "depth",
                                        0,
                                    ),

                                "reason":
                                    item.get(
                                        "reason",
                                        "",
                                    ),
                            }
                        )


                clean_asset_id = "unknown"

                if len(affected_assets) == 1:

                    clean_asset_id = affected_assets[0]

                elif len(affected_assets) > 1:

                    clean_asset_id = "multiple-containers"


                _diagnostic("ANALYZE 6 BEFORE APPEND")

                incidents.append(

                    {

                        "name":

                            "service_degradation",

                        "asset": asset_id,

                        "affected_assets": affected_assets,


                        "blast_radius": blast_radius,

                        "supporting_infrastructure":
                            supporting_infrastructure,




                        "confidence":

                            round(
                                confidence,
                                2
                            ),


                        "severity":

                            severity,


                        "evidence":

                            evidence,


                        "events":

                            evidence,


                        "recommendation":

                            "Inspect service logs and restart affected container if required.",


                        "root_cause":

                            (
                                (
                                    f"multiple docker containers unavailable: "
                                    f"{len(affected_assets)} affected"
                                )
                                if len(affected_assets) > 1
                                else
                                (
                                    f"container {clean_asset_id} unavailable"
                                    if clean_asset_id != "unknown"
                                    else "container unavailable"
                                )
                            ),


                        "diagnosis":

                            (
                                (
                                    "Multiple Docker containers stopped. "
                                    "Service degradation detected through correlated infrastructure events."
                                )
                                if len(affected_assets) > 1
                                else
                                (
                                    f"Container {clean_asset_id} stopped or unavailable. "
                                    "Service degradation detected through correlated events."
                                    if clean_asset_id != "unknown"
                                    else
                                    "Container unavailable. "
                                    "Service degradation detected through correlated events."
                                )
                            ),


                        "suggested_actions":

                            [
                                "Inspect service logs",
                                "Restart affected container",
                                "Verify dependencies",
                            ],

                    }

                )



            _diagnostic("ANALYZE END")
            return incidents
