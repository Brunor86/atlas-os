from atlas.storage.asset_repository import (
    AssetRepository,
)

from atlas.services.intelligence.operator_tools.base import (
    ToolDefinition,
    ToolResult,
)


class AssetTools:

    def __init__(
        self,
        repository=None,
    ):

        self.repository = (
            repository
            or AssetRepository()
        )


    def find_asset(
        self,
        query: str,
    ) -> ToolResult:

        if not query:

            return ToolResult(

                tool="find_asset",

                status="ERROR",

                error="query is required",

            )


        query = query.strip().lower()

        assets = (
            self.repository.get_all_assets()
        )


        matches = []

        for asset in assets:

            name = (
                asset.name or ""
            ).lower()

            asset_id = (
                asset.id or ""
            ).lower()


            if (
                query in name
                or query in asset_id
            ):

                matches.append(

                    {

                        "id":
                            asset.id,

                        "name":
                            asset.name,

                        "type":
                            asset.type.name,

                        "status":
                            asset.status.name,

                        "health":
                            asset.health,

                        "criticality":
                            asset.criticality.name,

                        "roles": [

                            role.name

                            for role
                            in asset.asset_roles

                        ],

                    }

                )


        return ToolResult(

            tool="find_asset",

            status="SUCCESS",

            result=matches,

            evidence=[

                (
                    f"{len(matches)} asset matches "
                    f"for query '{query}'"
                )

            ],

        )


    def inspect_asset(
        self,
        asset_id: str,
    ) -> ToolResult:

        if not asset_id:

            return ToolResult(

                tool="inspect_asset",

                status="ERROR",

                error="asset_id is required",

            )


        asset = self.repository.get_asset(
            asset_id
        )


        if not asset:

            return ToolResult(

                tool="inspect_asset",

                status="NOT_FOUND",

                error=(
                    f"Asset not found: {asset_id}"
                ),

            )


        result = {

            "id":
                asset.id,

            "name":
                asset.name,

            "type":
                asset.type.name,

            "status":
                asset.status.name,

            "health":
                asset.health,

            "criticality":
                asset.criticality.name,

            "roles": [

                role.name

                for role in asset.asset_roles

            ],

            "capabilities": [

                capability.name

                for capability
                in asset.capabilities

            ],

            "observations": [

                {

                    "type":
                        observation.type,

                    "value":
                        str(observation.value),

                    "severity":
                        observation.severity,

                    "source":
                        observation.source,

                    "timestamp":
                        observation.timestamp.isoformat(),

                }

                for observation
                in asset.observations

            ],

            "relationships": [

                {

                    "type":
                        relationship.type.name,

                    "source":
                        relationship.source,

                    "target":
                        relationship.target,

                }

                for relationship
                in asset.relationships

            ],

        }


        return ToolResult(

            tool="inspect_asset",

            status="SUCCESS",

            result=result,

            evidence=[

                "asset loaded from AssetRepository",

            ],

        )


    def get_asset_context(
        self,
        asset_id: str,
    ) -> ToolResult:

        if not asset_id:

            return ToolResult(
                tool="get_asset_context",
                status="ERROR",
                error="asset_id is required",
            )

        asset = self.repository.get_asset(
            asset_id
        )

        if not asset:

            return ToolResult(
                tool="get_asset_context",
                status="NOT_FOUND",
                error=(
                    f"Asset not found: {asset_id}"
                ),
            )

        result = {
            "asset": {
                "id": asset.id,
                "name": asset.name,
                "type": asset.type.name,
                "status": asset.status.name,
                "health": asset.health,
                "criticality": asset.criticality.name,
                "roles": [
                    role.name
                    for role in asset.asset_roles
                ],
                "capabilities": [
                    capability.name
                    for capability
                    in asset.capabilities
                ],
            },
            "identity": {
                "serial": asset.identity.serial,
                "model": asset.identity.model,
                "vendor": asset.identity.vendor,
                "firmware": asset.identity.firmware,
                "device": asset.identity.device,
            },
            "metadata": dict(
                asset.metadata
            ),
            "observations": [
                {
                    "type": observation.type,
                    "value": str(
                        observation.value
                    ),
                    "severity": observation.severity,
                    "source": observation.source,
                    "timestamp": (
                        observation.timestamp.isoformat()
                    ),
                }
                for observation
                in asset.observations
            ],
            "relationships": [
                {
                    "type": relationship.type.name,
                    "source": relationship.source,
                    "target": relationship.target,
                    "metadata": dict(
                        relationship.metadata
                    ),
                }
                for relationship
                in asset.relationships
            ],
        }

        return ToolResult(
            tool="get_asset_context",
            status="SUCCESS",
            result=result,
            evidence=[
                "asset context loaded from AssetRepository",
                (
                    f"{len(asset.observations)} observations "
                    "loaded"
                ),
                (
                    f"{len(asset.relationships)} relationships "
                    "loaded"
                ),
            ],
        )


    def list_assets(
        self,
        status: str | None = None,
        asset_type: str | None = None,
        criticality: str | None = None,
        role: str | None = None,
    ) -> ToolResult:

        assets = self.repository.get_all_assets()

        # -------------------------------------------------
        # Optional deterministic filters.
        #
        # Filtering happens at the AssetTools boundary so
        # callers such as the AI Operator can request only
        # the infrastructure relevant to the investigation.
        # -------------------------------------------------

        if status:
            status = status.strip().upper()
            assets = [
                asset
                for asset in assets
                if asset.status.name == status
            ]

        if asset_type:
            asset_type = asset_type.strip().upper()
            assets = [
                asset
                for asset in assets
                if asset.type.name == asset_type
            ]

        if criticality:
            criticality = criticality.strip().upper()
            assets = [
                asset
                for asset in assets
                if asset.criticality.name == criticality
            ]

        if role:
            role = role.strip().upper()
            assets = [
                asset
                for asset in assets
                if any(
                    asset_role.name == role
                    for asset_role in asset.asset_roles
                )
            ]

        result = [

            {
                "id": asset.id,
                "name": asset.name,
                "type": asset.type.name,
                "status": asset.status.name,
                "health": asset.health,
                "criticality": asset.criticality.name,
                "roles": [
                    role.name
                    for role in asset.asset_roles
                ],
                "capabilities": [
                    capability.name
                    for capability in asset.capabilities
                ],
            }

            for asset in assets

        ]

        filters = {}

        if status:
            filters["status"] = status

        if asset_type:
            filters["asset_type"] = asset_type

        if criticality:
            filters["criticality"] = criticality

        if role:
            filters["role"] = role

        if filters:
            evidence = [
                f"{len(result)} assets matched filters",
                f"filters={filters}",
            ]
        else:
            evidence = [
                f"{len(result)} assets loaded from AssetRepository"
            ]

        return ToolResult(

            tool="list_assets",

            status="SUCCESS",

            result=result,

            evidence=evidence,

        )


    def definitions(
        self,
    ):

        return [

            ToolDefinition(

                name="find_asset",

                description=(
                    "Find infrastructure assets by "
                    "name or asset identifier."
                ),

                handler=self.find_asset,

                read_only=True,

                requires_approval=False,

            ),

            ToolDefinition(

                name="get_asset_context",

                description=(
                    "Build a complete infrastructure context "
                    "for an asset including identity, metadata, "
                    "observations and relationships."
                ),

                handler=self.get_asset_context,
                read_only=True,
                requires_approval=False,

            ),

            ToolDefinition(

                name="list_assets",

                description=(
                    "List discovered infrastructure assets "
                    "with identity, status, health, roles "
                    "and capabilities. Supports optional "
                    "filters: status, asset_type, criticality "
                    "and role."
                ),

                handler=self.list_assets,

                read_only=True,

                requires_approval=False,

            ),

            ToolDefinition(

                name="inspect_asset",

                description=(
                    "Inspect an infrastructure asset "
                    "including status, health, roles, "
                    "capabilities and relationships."
                ),

                handler=self.inspect_asset,

                read_only=True,

                requires_approval=False,

            ),

        ]
