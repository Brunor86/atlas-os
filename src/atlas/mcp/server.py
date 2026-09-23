from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from atlas.services.semantic.api import (
    AtlasSemanticAPI,
)
from atlas.services.semantic.query import (
    SemanticQueryEngine,
)


class AtlasKnowledgeResult(BaseModel):

    status: str

    data: dict[str, Any]


READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    idempotent_hint=True,
    open_world_hint=False,
)


def _semantic_api() -> AtlasSemanticAPI:

    return AtlasSemanticAPI()


def _semantic_engine() -> SemanticQueryEngine:

    return SemanticQueryEngine()


def _wrap(
    result: dict[str, Any],
) -> AtlasKnowledgeResult:

    return AtlasKnowledgeResult(
        status=str(
            result.get(
                "status",
                "SUCCESS",
            )
        ),
        data=result,
    )


def _compact_status_result(
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    Keep verified status evidence compact for MCP consumers.

    Selector validation and inventory truth remain owned by
    AtlasSemanticAPI. This helper only reduces transport payload.
    """

    if (
        result.get(
            "status"
        )
        != "SUCCESS"
    ):
        return result

    compact_assets = []

    for asset in result.get(
        "assets",
        [],
    ):

        if not isinstance(
            asset,
            dict,
        ):
            continue

        compact_assets.append(
            {
                "id":
                    asset.get(
                        "id"
                    ),

                "name":
                    asset.get(
                        "name"
                    ),

                "type":
                    asset.get(
                        "type"
                    ),

                "status":
                    asset.get(
                        "status"
                    ),

                "health":
                    asset.get(
                        "health"
                    ),

                "criticality":
                    asset.get(
                        "criticality"
                    ),

                "roles":
                    list(
                        asset.get(
                            "roles",
                            [],
                        )
                        or []
                    ),

                "last_seen":
                    asset.get(
                        "last_seen"
                    ),
            }
        )

    return {
        "status":
            "SUCCESS",

        "complete":
            bool(
                result.get(
                    "complete"
                )
            ),

        "count":
            len(
                compact_assets
            ),

        "filters":
            dict(
                result.get(
                    "filters",
                    {},
                )
                or {}
            ),

        "assets":
            compact_assets,

        "evidence":
            list(
                result.get(
                    "evidence",
                    [],
                )
                or []
            ),
    }


def _normalized(
    value,
) -> str:

    return str(
        value
        or ""
    ).strip().lower()


def _identity_specificity(
    asset: dict[str, Any],
) -> int:
    """
    Generic tie-breaker for duplicate infrastructure identities.

    A VM/LXC is a more specific runtime representation than a generic
    SERVER asset when both expose the same exact human-readable name.

    This never identifies products or hosts by name.
    """

    asset_type = str(
        asset.get(
            "type"
        )
        or ""
    ).strip().upper()

    return {
        "VM": 30,
        "LXC": 30,
        "SERVER": 20,
    }.get(
        asset_type,
        0,
    )


def _match_rank(
    asset: dict[str, Any],
    query: str,
) -> tuple[int, str]:

    """
    Rank identity matches above references to an asset.

    Example:
        name=debian-docker
    must rank far above:
        docker_host=debian-docker
    """

    needle = _normalized(
        query
    )

    asset_id = _normalized(
        asset.get(
            "id"
        )
    )

    name = _normalized(
        asset.get(
            "name"
        )
    )

    metadata = (
        asset.get(
            "metadata"
        )
        or {}
    )

    if not isinstance(
        metadata,
        dict,
    ):
        metadata = {}

    compose_project = _normalized(
        metadata.get(
            "compose_project"
        )
    )

    compose_service = _normalized(
        metadata.get(
            "compose_service"
        )
    )

    container_name = _normalized(
        metadata.get(
            "container_name"
        )
    )

    hostname = _normalized(
        metadata.get(
            "hostname"
        )
    )

    docker_host = _normalized(
        metadata.get(
            "docker_host"
        )
    )

    if asset_id == needle:
        return (
            1200,
            "exact_id",
        )

    if name == needle:
        return (
            (
                1000
                + _identity_specificity(
                    asset
                )
            ),
            "exact_name",
        )

    if needle and name.startswith(
        needle
    ):
        return (
            850,
            "name_prefix",
        )

    if needle and needle in name:
        return (
            800,
            "name_contains",
        )

    if compose_project == needle:
        return (
            750,
            "compose_project",
        )

    if compose_service == needle:
        return (
            725,
            "compose_service",
        )

    if container_name == needle:
        return (
            700,
            "container_name",
        )

    if needle and needle in asset_id:
        return (
            650,
            "id_contains",
        )

    if hostname == needle:
        return (
            300,
            "hostname_reference",
        )

    if docker_host == needle:
        return (
            100,
            "docker_host_reference",
        )

    return (
        10,
        "semantic_reference",
    )


def _compact_metadata(
    metadata,
) -> dict[str, Any]:

    if not isinstance(
        metadata,
        dict,
    ):
        return {}

    keys = (
        "provider",
        "runtime",
        "hostname",
        "docker_host",
        "compose_project",
        "compose_service",
        "container_name",
        "image",
        "service_role",
        "classification_reason",
    )

    result = {}

    for key in keys:

        value = metadata.get(
            key
        )

        if value not in (
            None,
            "",
            [],
            {},
        ):
            result[
                key
            ] = value

    return result


def _compact_asset(
    asset: dict[str, Any],
) -> dict[str, Any]:

    return {
        "id":
            asset.get(
                "id"
            ),

        "name":
            asset.get(
                "name"
            ),

        "type":
            asset.get(
                "type"
            ),

        "status":
            asset.get(
                "status"
            ),

        "health":
            asset.get(
                "health"
            ),

        "criticality":
            asset.get(
                "criticality"
            ),

        "roles":
            asset.get(
                "roles",
                [],
            ),

        "capabilities":
            asset.get(
                "capabilities",
                [],
            ),

        "last_seen":
            asset.get(
                "last_seen"
            ),

        "metadata":
            _compact_metadata(
                asset.get(
                    "metadata"
                )
            ),
    }


def _compact_search(
    result: dict[str, Any],
    query: str,
    limit: int,
) -> dict[str, Any]:

    if (
        result.get(
            "status"
        )
        != "SUCCESS"
    ):
        return result

    raw_matches = (
        result.get(
            "matches"
        )
        or []
    )

    ranked = []

    for asset in raw_matches:

        if not isinstance(
            asset,
            dict,
        ):
            continue

        score, reason = (
            _match_rank(
                asset,
                query,
            )
        )

        ranked.append(
            (
                score,
                reason,
                asset,
            )
        )

    ranked.sort(
        key=lambda item: (
            -item[0],
            _normalized(
                item[2].get(
                    "name"
                )
            ),
        )
    )

    #
    # If we have strong identity matches, references such as
    # docker_host/hostname are not useful for entity resolution.
    #
    exact = [
        item
        for item in ranked
        if item[1] in {
            "exact_id",
            "exact_name",
        }
    ]

    strong = [
        item
        for item in ranked
        if item[0] >= 650
    ]

    #
    # Exact identity matches suppress secondary references.
    #
    # Example:
    #   search("host-a")
    #
    # should return assets actually named host-a rather than every
    # service whose canonical id happens to contain host-a.
    #
    # If no exact identity exists, semantic/prefix/group matches
    # remain available for queries such as a Compose project name.
    #
    if exact:
        selected = exact

    elif strong:
        selected = strong

    else:
        selected = ranked

    selected = selected[
        :limit
    ]

    matches = []

    seen = set()

    for score, reason, asset in selected:

        asset_id = asset.get(
            "id"
        )

        if asset_id in seen:
            continue

        seen.add(
            asset_id
        )

        compact = (
            _compact_asset(
                asset
            )
        )

        compact[
            "match_score"
        ] = score

        compact[
            "match_reason"
        ] = reason

        matches.append(
            compact
        )

    return {
        "status":
            "SUCCESS",

        "query":
            query,

        "count":
            len(matches),

        "total_candidates":
            len(raw_matches),

        "matches":
            matches,
    }



def _compact_relation_result(
    api: AtlasSemanticAPI,
    result: dict[str, Any],
    *,
    relationship: str | None = None,
) -> dict[str, Any]:

    if result.get("status") != "SUCCESS":
        return result

    requested_relationship = (
        str(relationship).strip().upper()
        if relationship
        else None
    )

    compact_results = []

    for item in result.get(
        "results",
        [],
    ):

        if not isinstance(
            item,
            dict,
        ):
            continue

        relation = str(
            item.get(
                "relationship",
                "",
            )
        ).upper()

        if (
            requested_relationship
            and relation
            != requested_relationship
        ):
            continue

        asset_id = item.get(
            "asset_id"
        )

        name = None
        asset_type = None
        status = None

        if asset_id:

            peer = api.asset(
                asset_id
            )

            peer_asset = (
                peer.get(
                    "asset"
                )
                if isinstance(
                    peer,
                    dict,
                )
                else None
            )

            if isinstance(
                peer_asset,
                dict,
            ):

                name = peer_asset.get(
                    "name"
                )

                asset_type = (
                    peer_asset.get(
                        "type"
                    )
                )

                status = peer_asset.get(
                    "status"
                )

        compact_results.append(
            {
                "asset_id":
                    asset_id,

                "name":
                    name,

                "type":
                    asset_type,

                "status":
                    status,

                "relationship":
                    item.get(
                        "relationship"
                    ),

                "direction":
                    item.get(
                        "direction"
                    ),

                "depth":
                    item.get(
                        "depth"
                    ),

                "confidence":
                    item.get(
                        "confidence"
                    ),

                "evidence":
                    item.get(
                        "evidence",
                        [],
                    ),
            }
        )

    asset = result.get(
        "asset"
    )

    if isinstance(
        asset,
        dict,
    ):
        asset = _compact_asset(
            asset
        )

    return {
        "status":
            "SUCCESS",

        "asset":
            asset,

        "direction":
            result.get(
                "direction"
            ),

        "depth":
            result.get(
                "depth"
            ),

        "relationship":
            requested_relationship,

        "count":
            len(
                compact_results
            ),

        "results":
            compact_results,
    }

def _compact_semantic_relation_result(
    result: dict[str, Any],
) -> dict[str, Any]:

    if result.get("status") != "SUCCESS":
        return result

    orientation = str(
        result.get(
            "orientation",
            ""
        )
    ).strip().upper()

    direction = (
        "DOWNSTREAM"
        if orientation == "OUTGOING"
        else "UPSTREAM"
    )

    compact_results = []

    for item in result.get(
        "results",
        [],
    ):

        if not isinstance(
            item,
            dict,
        ):
            continue

        if orientation == "OUTGOING":
            peer_id = item.get(
                "target_asset_id"
            )
            peer_name = item.get(
                "target_name"
            )
        else:
            peer_id = item.get(
                "source_asset_id"
            )
            peer_name = item.get(
                "source_name"
            )

        compact_results.append(
            {
                "asset_id":
                    peer_id,

                "name":
                    peer_name,

                "relationship":
                    item.get(
                        "relationship"
                    ),

                "direction":
                    direction,

                "depth":
                    item.get(
                        "depth"
                    ),

                "confidence":
                    item.get(
                        "confidence"
                    ),

                "evidence":
                    list(
                        item.get(
                            "evidence",
                            [],
                        )
                        or []
                    ),

                "root_member_id":
                    item.get(
                        "root_member_id"
                    ),

                "source_asset_id":
                    item.get(
                        "source_asset_id"
                    ),

                "source_name":
                    item.get(
                        "source_name"
                    ),

                "target_asset_id":
                    item.get(
                        "target_asset_id"
                    ),

                "target_name":
                    item.get(
                        "target_name"
                    ),
            }
        )

    return {
        "status":
            "SUCCESS",

        "entity":
            result.get(
                "entity"
            ),

        "relationship":
            result.get(
                "relationship"
            ),

        "direction":
            direction,

        "depth":
            result.get(
                "depth"
            ),

        "count":
            len(
                compact_results
            ),

        "results":
            compact_results,
    }


def build_server() -> MCPServer:

    server = MCPServer(
        "atlas-knowledge",
        instructions=(
            "Read-only access to ATLAS infrastructure knowledge. "
            "Search before describing an entity. "
            "Prefer canonical asset facts and topology over assumptions. "
            "Never infer infrastructure state when ATLAS can be queried."
        ),
    )

    @server.tool(
        name="atlas_resolve_entity",
        title="Resolve an ATLAS semantic entity",
        description=(
            "Resolve human-readable infrastructure text to one canonical "
            "ATLAS semantic entity. The result may be an ASSET, GROUP, "
            "AMBIGUOUS entity or NOT_FOUND. Prefer this when the user refers "
            "to a logical application, stack, cluster, service group or other "
            "human-readable infrastructure concept."
        ),
        annotations=READ_ONLY,
    )
    def atlas_resolve_entity(
        query: Annotated[
            str,
            Field(
                min_length=1,
                max_length=200,
            ),
        ],
    ) -> AtlasKnowledgeResult:

        return _wrap(
            _semantic_api()
            .resolve_entity(
                query
            )
        )


    @server.tool(
        name="atlas_query_entity_relations",
        title="Query semantic entity relationships",
        description=(
            "Traverse canonical ATLAS relationships for a human-readable "
            "semantic entity or logical group. The entity argument accepts "
            "either the original human-readable query or the canonical reference "
            "returned by atlas_resolve_entity. Groups are expanded internally; "
            "do not query every member separately. DEPENDS_ON points from the "
            "consumer to its dependency. Use direction='downstream' to find "
            "what an entity depends on and direction='upstream' to find what "
            "depends on the entity."
        ),
        annotations=READ_ONLY,
    )
    def atlas_query_entity_relations(
        entity: Annotated[
            str,
            Field(
                min_length=1,
                max_length=300,
            ),
        ],
        direction: Literal[
            "upstream",
            "downstream",
        ] = "downstream",
        relationship: Annotated[
            str | None,
            Field(
                max_length=64,
            ),
        ] = None,
        depth: Annotated[
            int,
            Field(
                ge=1,
                le=3,
            ),
        ] = 1,
    ) -> AtlasKnowledgeResult:

        result = (
            _semantic_api()
            .entity_relations(
                entity,
                relationship=relationship,
                direction=direction,
                depth=depth,
            )
        )

        return _wrap(
            _compact_semantic_relation_result(
                result
            )
        )


    @server.tool(
        name="atlas_search_assets",
        title="Search ATLAS assets",
        description=(
            "Search canonical ATLAS assets by human-readable text. "
            "Results are ranked by identity and intentionally compact. "
            "Use atlas_describe_asset after selecting the desired asset."
        ),
        annotations=READ_ONLY,
    )
    def atlas_search_assets(
        query: Annotated[
            str,
            Field(
                min_length=1,
                max_length=200,
            ),
        ],
        limit: Annotated[
            int,
            Field(
                ge=1,
                le=20,
            ),
        ] = 10,
    ) -> AtlasKnowledgeResult:

        result = (
            _semantic_api()
            .find(
                query
            )
        )

        return _wrap(
            _compact_search(
                result,
                query,
                limit,
            )
        )

    @server.tool(
        name="atlas_describe_asset",
        title="Describe an ATLAS asset",
        description=(
            "Return compact canonical information for one ATLAS asset. "
            "Use an asset id returned by atlas_search_assets."
        ),
        annotations=READ_ONLY,
    )
    def atlas_describe_asset(
        asset_id: Annotated[
            str,
            Field(
                min_length=1,
                max_length=300,
            ),
        ],
    ) -> AtlasKnowledgeResult:

        result = (
            _semantic_api()
            .asset(
                asset_id
            )
        )

        if (
            result.get(
                "status"
            )
            == "SUCCESS"
            and isinstance(
                result.get(
                    "asset"
                ),
                dict,
            )
        ):

            result = {
                "status":
                    "SUCCESS",

                "asset":
                    _compact_asset(
                        result[
                            "asset"
                        ]
                    ),
            }

        return _wrap(
            result
        )

    @server.tool(
        name="atlas_query_relations",
        title="Query ATLAS relationships",
        description=(
            "Traverse canonical infrastructure relationships for an asset. "
            "Relationship edges follow their canonical source-to-target "
            "direction. DEPENDS_ON points from the consumer to its dependency. "
            "Therefore, to find what an asset depends on, use "
            "direction='downstream', relationship='DEPENDS_ON', depth=1. "
            "To find assets that depend on it, use direction='upstream', "
            "relationship='DEPENDS_ON', depth=1. "
            "Use the optional relationship filter whenever the requested "
            "relationship type is known."
        ),
        annotations=READ_ONLY,
    )
    def atlas_query_relations(
        asset_id: Annotated[
            str,
            Field(
                min_length=1,
                max_length=300,
            ),
        ],
        direction: Literal[
            "neighbors",
            "upstream",
            "downstream",
        ] = "neighbors",
        relationship: Annotated[
            str | None,
            Field(
                max_length=64,
            ),
        ] = None,
        depth: Annotated[
            int,
            Field(
                ge=1,
                le=3,
            ),
        ] = 2,
    ) -> AtlasKnowledgeResult:

        api = _semantic_api()

        result = api.topology(
            asset_id,
            direction=direction,
            depth=depth,
        )

        return _wrap(
            _compact_relation_result(
                api,
                result,
                relationship=relationship,
            )
        )

    @server.tool(
        name="atlas_query_impact",
        title="Query ATLAS impact",
        description=(
            "Calculate downstream impact for one canonical ATLAS asset."
        ),
        annotations=READ_ONLY,
    )
    def atlas_query_impact(
        asset_id: Annotated[
            str,
            Field(
                min_length=1,
                max_length=300,
            ),
        ],
        depth: Annotated[
            int,
            Field(
                ge=1,
                le=3,
            ),
        ] = 3,
    ) -> AtlasKnowledgeResult:

        return _wrap(
            _semantic_api().impact(
                asset_id,
                depth=depth,
            )
        )

    @server.tool(
        name="atlas_query_asset_status",
        title="Query canonical ATLAS asset status",
        description=(
            "Query current canonical asset inventory using structured "
            "ATLAS selectors. Supports status, asset type, criticality "
            "and asset role filters. Selector values must use canonical "
            "ATLAS ontology names such as ONLINE, OFFLINE, DEGRADED, "
            "APPLICATION, SERVER or MONITORING_NODE. A successful "
            "complete result with count=0 is verified evidence that no "
            "currently registered asset matches the supplied selectors."
        ),
        annotations=READ_ONLY,
    )
    def atlas_query_asset_status(
        status: Annotated[
            str | None,
            Field(
                max_length=64,
            ),
        ] = None,
        asset_type: Annotated[
            str | None,
            Field(
                max_length=64,
            ),
        ] = None,
        criticality: Annotated[
            str | None,
            Field(
                max_length=64,
            ),
        ] = None,
        role: Annotated[
            str | None,
            Field(
                max_length=64,
            ),
        ] = None,
    ) -> AtlasKnowledgeResult:

        result = (
            _semantic_api()
            .query_asset_status(
                status=status,
                asset_type=asset_type,
                criticality=criticality,
                role=role,
            )
        )

        return _wrap(
            _compact_status_result(
                result
            )
        )


    @server.tool(
        name="atlas_attention_summary",
        title="Summarize operational attention",
        description=(
            "Return current verified ATLAS operational signals that "
            "require attention. This consolidates current operational events, "
            "unresolved incidents and configured current health sources. "
            "Use this for questions "
            "about current problems, warnings, alerts, anomalies or what "
            "needs attention."
        ),
        annotations=READ_ONLY,
    )
    def atlas_attention_summary(
    ) -> AtlasKnowledgeResult:

        return _wrap(
            _semantic_api().attention()
        )


    @server.tool(
        name="atlas_semantic_query",
        title="Ask ATLAS semantic knowledge",
        description=(
            "Ask a short deterministic infrastructure question. "
            "Prefer search, describe and relations for multi-step investigation."
        ),
        annotations=READ_ONLY,
    )
    def atlas_semantic_query(
        question: Annotated[
            str,
            Field(
                min_length=1,
                max_length=500,
            ),
        ],
    ) -> AtlasKnowledgeResult:

        return _wrap(
            _semantic_engine().query(
                question
            )
        )

    return server


mcp = build_server()


if __name__ == "__main__":
    mcp.run()
