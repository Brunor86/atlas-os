
from atlas.storage.asset_repository import AssetRepository
from atlas.services.assets.topology_traversal import TopologyTraversalService


class BlastRadiusEngine:


    def __init__(self):

        self.assets = AssetRepository()
        self.topology = TopologyTraversalService()



    def analyze(
        self,
        asset_id,
        depth=5,
    ):

        asset = self.assets.get_asset(
            asset_id
        )


        if not asset:

            return {
                "error": "asset not found"
            }



        affected = self.topology.downstream(
            asset_id,
            depth=depth,
        )


        services = []


        for item in affected:

            child = self.assets.get_asset(
                item["asset_id"]
            )


            if not child:
                continue


            services.append(
                {
                    "id": child.id,
                    "name": child.name,
                    "type": child.type.name,
                    "roles": [
                        r.name
                        for r in child.asset_roles
                    ],
                    "criticality":
                        child.criticality.name,
                    "relationship":
                        item["relationship"],
                    "depth":
                        item.get(
                            "depth",
                            0
                        ),
                }
            )



        score = self._calculate_score(
            services
        )


        return {

            "asset": {

                "id": asset.id,
                "name": asset.name,
                "type": asset.type.name,

            },


            "affected_count":
                len(services),


            "impact_score":
                score,


            "affected_assets":
                services,

        }



    def _calculate_score(
        self,
        services,
    ):

        weights = {

            "LOW":10,
            "MEDIUM":30,
            "HIGH":70,
            "CRITICAL":100,

        }


        score = 0


        for service in services:

            score += weights.get(
                service["criticality"],
                10
            )


        return score
