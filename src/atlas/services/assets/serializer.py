from atlas.core.asset import Asset


class AssetSerializer:


    def serialize(self, asset: Asset):

        return {

            "id": asset.id,

            "name": asset.name,

            "type": asset.type.name,

            "status": asset.status.name,

            "health": asset.health,

            "criticality": asset.criticality.name,


            "identity": {

                "model": asset.identity.model,

                "serial": asset.identity.serial,

                "vendor": asset.identity.vendor,

                "firmware": asset.identity.firmware,

                "device": asset.identity.device,

            },


            "capabilities": [

                capability.name

                for capability in asset.capabilities

            ],


            "observations": [

                {

                    "type": obs.type,

                    "value": obs.value,

                    "severity": obs.severity,

                    "source": obs.source,

                    "timestamp": obs.timestamp.isoformat(),

                }

                for obs in asset.observations

            ],


            "last_seen":

                asset.last_seen.isoformat(),

        }
