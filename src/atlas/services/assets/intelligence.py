from atlas.storage.asset_repository import AssetRepository
from atlas.services.assets.topology_traversal import TopologyTraversalService
from atlas.services.noc.impact import ImpactEngine


class AssetIntelligenceService:


    def __init__(self):

        self.assets = AssetRepository()

        self.topology = TopologyTraversalService()

        self.impact = ImpactEngine()



    def analyze(
        self,
        asset_id,
    ):

        asset = self.assets.get_asset(
            asset_id
        )


        if not asset:

            return {
                "error": "asset not found"
            }



        impact = self.impact.analyze(
            asset_id
        )


        upstream = self.topology.critical_upstream(
            asset_id
        )


        downstream = self.topology.downstream(
            asset_id
        )



        return {

            "asset": {

                "id": asset.id,

                "name": asset.name,

                "type": asset.type.name,

                "status": asset.status.name,

                "criticality":
                    asset.criticality.name,

                "roles":
                    [
                        r.name
                        for r in asset.asset_roles
                    ],

            },


            "topology": {

                "upstream": upstream,

                "downstream": downstream,

                "upstream_count":
                    len(upstream),

                "downstream_count":
                    len(downstream),

            },


            "impact": {

                "score":
                    impact.get(
                        "impact_score"
                    ),

                "severity":
                    impact.get(
                        "severity"
                    ),

                "root_causes":
                    impact.get(
                        "root_causes",
                        []
                    ),

            },


            "capabilities":
                [
                    c.name
                    for c in asset.capabilities
                ],


            "observations":
                asset.observations,


        }
