from atlas.services.knowledge.builders.base import KnowledgeBuilder


class ServerBuilder(KnowledgeBuilder):


    def build(
        self,
        asset,
        card,
        graph,
    ):


        card.observations.append(

            f"Hosts {len(card.dependencies)} dependent assets."

        )


        summary = [

            f"{card.asset_name} is a server.",


            "Roles: "
            +
            ", ".join(card.roles)
            +
            ".",


            f"Currently connected to {len(card.dependencies)} assets.",

        ]


        card.summary = " ".join(summary)
