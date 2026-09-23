from atlas.models.impact import ImpactNode


class ImpactSerializer:

    def node(
        self,
        data,
    ):

        return {

            "asset_id":
                data.get("asset_id"),

            "relationship":
                data.get(
                    "relationship"
                ),

            "depth":
                data.get(
                    "depth",
                    0
                ),

            "weight":
                data.get(
                    "weight",
                    0
                ),

            "impact_score":
                data.get(
                    "impact_score",
                    0
                ),
        }


    def serialize(
        self,
        impact,
    ):

        upstream = [
            self.node(x)
            for x in impact.get(
                "operational_upstream",
                []
            )
        ]

        root_causes = [
            self.node(x)
            for x in impact.get(
                "root_causes",
                []
            )
        ]

        downstream = [
            self.node(x)
            for x in impact.get(
                "downstream",
                []
            )
        ]

        affected_assets = []

        seen = set()

        for node in (
            upstream
            + root_causes
            + downstream
        ):

            asset_id = node.get(
                "asset_id"
            )

            if (
                asset_id
                and asset_id not in seen
            ):

                seen.add(
                    asset_id
                )

                affected_assets.append(
                    asset_id
                )


        return {

            "asset":
                impact.get(
                    "asset"
                ),

            "severity":
                impact.get(
                    "severity"
                ),

            "score":
                impact.get(
                    "impact_score"
                ),

            "affected_assets":
                affected_assets,

            "upstream":
                upstream,

            "root_causes":
                root_causes,

            "downstream":
                downstream,
        }
