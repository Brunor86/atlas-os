from atlas.services.knowledge.builders.server import ServerBuilder
from atlas.services.knowledge.builders.container import ContainerBuilder


class BuilderFactory:


    def __init__(self):

        self.builders = {

            "SERVER":
                ServerBuilder(),


            "CONTAINER":
                ContainerBuilder(),

        }



    def get(
        self,
        asset_type,
    ):

        return self.builders.get(
            asset_type
        )
