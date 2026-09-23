from atlas.core.asset import AssetType

from atlas.core.relationship import (
    Relationship,
    RelationshipType,
)

from atlas.storage.graph_repository import GraphRepository



class TopologyService:


    def __init__(self):

        self.repository = GraphRepository()



    def build(
        self,
        assets: list,
    ):


        servers = [
            a
            for a in assets
            if a.type == AssetType.SERVER
        ]


        docker_services = [
            a
            for a in assets
            if (
                a.type == AssetType.SERVICE
                and a.name == "docker"
            )
        ]


        containers = [
            a
            for a in assets
            if a.type == AssetType.CONTAINER
        ]



        relationships = []



        #
        # SERVER -> DOCKER
        #

        for server in servers:

            for docker in docker_services:


                relationship = Relationship(

                    source=server.id,

                    target=docker.id,

                    type=RelationshipType.PROVIDES,

                    confidence=0.98,

                    evidence=[
                        "server inventory",
                        "docker service discovery",
                        "topology provider relationship",
                    ],

                    metadata={
                        "discovered_by": "topology",
                    }

                )


                self.repository.save_relationship(
                    relationship
                )


                server.add_relationship(
                    relationship
                )


                relationships.append(
                    relationship
                )



        #
        # DOCKER -> CONTAINERS
        #

        for docker in docker_services:

            for container in containers:


                relationship = Relationship(

                    source=docker.id,

                    target=container.id,

                    type=RelationshipType.RUNS,

                    confidence=0.98,

                    evidence=[
                        "docker runtime discovery",
                        "container inventory",
                        "topology provider relationship",
                    ],

                    metadata={
                        "discovered_by": "topology",
                    }

                )


                self.repository.save_relationship(
                    relationship
                )


                docker.add_relationship(
                    relationship
                )


                relationships.append(
                    relationship
                )



        return relationships
