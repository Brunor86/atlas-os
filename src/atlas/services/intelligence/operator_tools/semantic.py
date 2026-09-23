from __future__ import annotations

from atlas.services.semantic.api import AtlasSemanticAPI

from atlas.services.intelligence.operator_tools.base import (
    ToolDefinition,
    ToolResult,
)


class SemanticTools:

    def __init__(
        self,
        semantic: AtlasSemanticAPI | None = None,
    ):
        self.semantic = (
            semantic
            or AtlasSemanticAPI()
        )

    def find(
        self,
        query: str,
    ) -> ToolResult:

        try:
            return ToolResult(
                tool="atlas_find",
                status="SUCCESS",
                result=self.semantic.find(query),
                evidence=[
                    "semantic asset discovery"
                ],
            )

        except Exception as exc:
            return ToolResult(
                tool="atlas_find",
                status="ERROR",
                error=str(exc),
            )

    def asset(
        self,
        asset_id: str,
    ) -> ToolResult:

        try:
            result = self.semantic.asset(
                asset_id
            )

            return ToolResult(
                tool="atlas_get_asset",
                status=result.get(
                    "status",
                    "SUCCESS",
                ),
                result=result,
                evidence=[
                    "semantic asset context"
                ],
            )

        except Exception as exc:
            return ToolResult(
                tool="atlas_get_asset",
                status="ERROR",
                error=str(exc),
            )

    def assets(
        self,
        query: str | None = None,
        status: str | None = None,
        asset_type: str | None = None,
        criticality: str | None = None,
        role: str | None = None,
    ) -> ToolResult:

        try:
            result = self.semantic.assets(
                query=query,
                status=status,
                asset_type=asset_type,
                criticality=criticality,
                role=role,
            )

            return ToolResult(
                tool="atlas_list_assets",
                status="SUCCESS",
                result=result,
                evidence=[
                    "semantic infrastructure inventory"
                ],
            )

        except Exception as exc:
            return ToolResult(
                tool="atlas_list_assets",
                status="ERROR",
                error=str(exc),
            )

    def attention(self) -> ToolResult:

        try:

            result = self.semantic.attention()

            return ToolResult(
                tool="atlas_get_attention",
                status=result.get(
                    "status",
                    "SUCCESS",
                ),
                result=result,
                evidence=[
                    "current operational attention summary"
                ],
            )

        except Exception as exc:

            return ToolResult(
                tool="atlas_get_attention",
                status="ERROR",
                error=str(exc),
            )


    def infrastructure(self) -> ToolResult:

        try:
            return ToolResult(
                tool="atlas_get_infrastructure",
                status="SUCCESS",
                result=self.semantic.infrastructure(),
                evidence=[
                    "complete semantic infrastructure inventory"
                ],
            )

        except Exception as exc:
            return ToolResult(
                tool="atlas_get_infrastructure",
                status="ERROR",
                error=str(exc),
            )

    def topology(
        self,
        asset_id: str,
        direction: str = "neighbors",
        depth: int = 5,
    ) -> ToolResult:

        try:
            result = self.semantic.topology(
                asset_id=asset_id,
                direction=direction,
                depth=depth,
            )

            return ToolResult(
                tool="atlas_get_topology",
                status=result.get(
                    "status",
                    "SUCCESS",
                ),
                result=result,
                evidence=[
                    "semantic topology traversal"
                ],
            )

        except Exception as exc:
            return ToolResult(
                tool="atlas_get_topology",
                status="ERROR",
                error=str(exc),
            )

    def impact(
        self,
        asset_id: str,
        depth: int = 5,
    ) -> ToolResult:

        try:
            result = self.semantic.impact(
                asset_id=asset_id,
                depth=depth,
            )

            return ToolResult(
                tool="atlas_get_impact",
                status=result.get(
                    "status",
                    "SUCCESS",
                ),
                result=result,
                evidence=[
                    "semantic infrastructure impact analysis"
                ],
            )

        except Exception as exc:
            return ToolResult(
                tool="atlas_get_impact",
                status="ERROR",
                error=str(exc),
            )

    def definitions(self) -> list[ToolDefinition]:

        return [

            ToolDefinition(
                name="atlas_find",
                description=(
                    "Find infrastructure assets semantically by "
                    "name, ID, hostname, VMID, serial, model, "
                    "device, metadata or role. Use this first when "
                    "the user refers to an infrastructure object "
                    "by name."
                ),
                handler=self.find,
                read_only=True,
                requires_approval=False,
                capabilities=(
                    "ASSET_DISCOVERY",
                    "SEMANTIC_SEARCH",
                ),
            ),

            ToolDefinition(
                name="atlas_get_asset",
                description=(
                    "Get the complete semantic context of an ATLAS "
                    "asset including identity, metadata, status, "
                    "roles, observations, capabilities and topology."
                ),
                handler=self.asset,
                read_only=True,
                requires_approval=False,
                capabilities=(
                    "ASSET_CONTEXT",
                ),
            ),

            ToolDefinition(
                name="atlas_list_assets",
                description=(
                    "List ATLAS infrastructure assets with optional "
                    "filters for query, status, type, criticality "
                    "and role. Use for questions about VMs, LXC, "
                    "Docker containers, applications, storage, "
                    "servers or services."
                ),
                handler=self.assets,
                read_only=True,
                requires_approval=False,
                capabilities=(
                    "ASSET_INVENTORY",
                ),
            ),

            ToolDefinition(
                name="atlas_get_attention",
                description=(
                    "Return current verified operational signals that "
                    "require attention, including active events and "
                    "unresolved incidents. Use for questions about "
                    "current problems, warnings, alerts, anomalies, "
                    "operational health or what needs attention."
                ),
                handler=self.attention,
                read_only=True,
                requires_approval=False,
                capabilities=(
                    "OPERATIONAL_ATTENTION",
                    "HEALTH",
                    "INCIDENTS",
                ),
                routing_hints=(
                    "necesita atención",
                    "necesita atencion",
                    "requiere atención",
                    "requiere atencion",
                    "qué necesita atención",
                    "que necesita atencion",
                    "qué requiere atención",
                    "que requiere atencion",
                    "problemas actuales",
                    "alertas actuales",
                    "advertencias actuales",
                    "estado operativo",
                    "salud operativa",
                    "needs attention",
                    "what needs attention",
                    "requires attention",
                    "current problems",
                    "current warnings",
                    "current alerts",
                    "operational attention",
                    "operational health",
                ),
            ),

            ToolDefinition(
                name="atlas_get_infrastructure",
                description=(
                    "Return the semantic inventory of the complete "
                    "ATLAS infrastructure grouped into servers, "
                    "VMs, LXC, containers, applications, databases, "
                    "storage, network, sensors and services."
                ),
                handler=self.infrastructure,
                read_only=True,
                requires_approval=False,
                capabilities=(
                    "INFRASTRUCTURE_INVENTORY",
                ),
            ),

            ToolDefinition(
                name="atlas_get_topology",
                description=(
                    "Traverse ATLAS infrastructure topology. Supports "
                    "neighbors, dependencies, dependents, upstream, "
                    "downstream, critical_upstream, "
                    "operational_upstream, blast_radius and impact. "
                    "Use for dependency and relationship questions."
                ),
                handler=self.topology,
                read_only=True,
                requires_approval=False,
                capabilities=(
                    "TOPOLOGY",
                    "KNOWLEDGE_GRAPH",
                ),
            ),

            ToolDefinition(
                name="atlas_get_impact",
                description=(
                    "Analyze the operational impact and downstream "
                    "blast radius of an ATLAS asset. Use for questions "
                    "such as what would be affected if a VM, server, "
                    "application, container or infrastructure component "
                    "fails."
                ),
                handler=self.impact,
                read_only=True,
                requires_approval=False,
                capabilities=(
                    "IMPACT_ANALYSIS",
                    "BLAST_RADIUS",
                ),
            ),
        ]
