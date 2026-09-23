from atlas.services.knowledge.models import KnowledgeCard
from atlas.services.knowledge.graph import GraphService
from atlas.services.knowledge.builders.factory import BuilderFactory
from atlas.services.assets.runtime import get_asset_registry


class KnowledgeEngine:

    def __init__(self, registry=None):

        self.registry = registry or get_asset_registry()

        self.graph = GraphService(self.registry)

        self.factory = BuilderFactory()


    def build(
        self,
        asset,
    ):

        dependencies = self.graph.get_dependencies(
            asset.id
        )

        dependents = self.graph.get_dependents(
            asset.id
        )

        card = KnowledgeCard(

            asset_id=asset.id,

            asset_name=asset.name,

            asset_type=asset.type.name,

            dependencies=[
                item["target"]
                for item in dependencies
            ],

            dependents=[
                item["source"]
                for item in dependents
            ],

            roles=[
                role.name
                for role in asset.asset_roles
            ],

            criticality=asset.criticality.name,

            role_weight=asset.role_weight(),

            relationship_count=(
                len(dependencies)
                +
                len(dependents)
            ),

            capabilities=[
                capability.name
                for capability in asset.capabilities
            ],

        )


        builder = self.factory.get(
            card.asset_type
        )


        if builder:

            builder.build(

                asset,

                card,

                self.graph,

            )


        return card


    def build_all(
        self,
        assets,
    ):

        return [

            self.build(
                asset
            )

            for asset in assets

        ]

