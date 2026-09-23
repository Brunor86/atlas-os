from atlas.core.infrastructure import Infrastructure


class ContextBuilder:


    def build(
        self,
        infra: Infrastructure,
    ) -> dict:


        assets = []


        #
        # Docker assets
        #

        for container in infra.docker.containers:

            assets.append(
                {
                    "id": container.name,
                    "name": container.name,
                    "type": "container",
                    "history": {},
                }
            )


        #
        # Storage assets
        #

        for disk in infra.storage:

            assets.append(
                {
                    "id": disk.mountpoint,
                    "name": disk.mountpoint,
                    "type": "storage",
                    "history": {},
                }
            )



        return {

            "system": {

                "hostname":
                    infra.system.hostname,

                "os":
                    infra.system.os_name,

            },


            "assets": {

                "inventory":
                    assets,

            },


            "health": {

                "findings":
                    [],

            },


            "docker": {

                "containers":
                    len(infra.docker.containers),

            },


            "storage": {

                "disks":
                    len(infra.storage),

            },

        }
