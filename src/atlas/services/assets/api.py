
from atlas.storage.asset_repository import AssetRepository

from atlas.services.noc.orchestrator import NOCOrchestrator
from atlas.services.assets.context_builder import AssetContextBuilder
from atlas.services.assets.context_service import AssetContextService


class AssetAPIService:

    def __init__(self):
        self.repository = AssetRepository()


    def list_assets(self):

        assets = self.repository.get_active_assets()

        ignored_types = {
            "SERVICE",
        }

        assets = [
            asset
            for asset in assets
            if asset.type.name not in ignored_types
            or asset.criticality.name in {
                "HIGH",
                "CRITICAL",
            }
        ]

        return [
            {
                "id": asset.id,
                "name": asset.name,
                "type": asset.type.name,
                "status": asset.status.name,
                "health": asset.health,
                "criticality": asset.criticality.name,
                "last_seen": asset.last_seen.isoformat(),
                "presence": asset.presence.name,
            }
            for asset in assets
        ]




    def overview(self):

        assets = self.repository.get_active_assets()


        summary = {
            "total": len(assets),
            "online": 0,
            "offline": 0,
            "degraded": 0,
            "critical": 0,
        }


        ranked = []


        for asset in assets:


            if asset.status.name == "ONLINE":
                summary["online"] += 1

            elif asset.status.name == "OFFLINE":
                summary["offline"] += 1

            else:
                summary["degraded"] += 1



            if asset.criticality.name in {
                "HIGH",
                "CRITICAL"
            }:
                summary["critical"] += 1



            ranked.append(
                {
                    "id": asset.id,
                    "name": asset.name,
                    "type": asset.type.name,
                    "criticality": asset.criticality.name,
                    "weight": asset.role_weight(),
                    "roles": [
                        r.name
                        for r in asset.asset_roles
                    ],
                }
            )


        ranked.sort(
            key=lambda x: x["weight"],
            reverse=True
        )


        return {
            "summary": summary,
            "top_assets": ranked[:10]
        }

    def get_asset(
        self,
        asset_id,
    ):

        asset = self.repository.get_asset(
            asset_id
        )

        if not asset:
            return None


        return {
            "id": asset.id,
            "name": asset.name,
            "type": asset.type.name,
            "status": asset.status.name,
            "health": asset.health,
            "criticality": asset.criticality.name,
            "last_seen": asset.last_seen.isoformat(),
            "presence": asset.presence.name,
            "presence_changed_at": (
                asset.presence_changed_at.isoformat()
                if asset.presence_changed_at
                else None
            ),

            "observations": [
                {
                    "type": obs.type,
                    "value": str(obs.value),
                    "severity": obs.severity,
                    "source": obs.source,
                    "timestamp": obs.timestamp.isoformat(),
                }
                for obs in asset.observations
            ],

            "relationships": [
                {
                    "type": rel.type.name,
                    "source": rel.source,
                    "target": rel.target,
                }
                for rel in asset.relationships
            ],
        }




    def get_context(
        self,
        asset_id,
    ):

        from atlas.services.assets.registry import AssetRegistry
        from atlas.services.assets.context_builder import AssetContextBuilder
        from atlas.services.assets.context_service import AssetContextService


        registry = AssetRegistry()


        asset = self.repository.get_asset(
            asset_id
        )


        if not asset:
            return None


        registry.register(
            asset
        )


        service = AssetContextService(
            AssetContextBuilder(
                registry
            )
        )


        context = service.get(
            asset_id
        )


        if not context:
            return None


        return context.__dict__
