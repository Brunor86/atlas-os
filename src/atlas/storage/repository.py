import json

from atlas.storage.database import Database


class SnapshotRepository:


    def __init__(self):

        self.database = Database()



    def get_latest(self):

        snapshot = self.database.get_last_snapshot()


        if not snapshot:

            return None


        created_at, data = snapshot


        return {

            "created_at": created_at,

            "data": json.loads(data),

        }



    def get_history(self, limit=10):

        snapshots = self.database.get_snapshots(limit)


        history = []


        for snapshot in snapshots:

            snapshot_id, created_at, data = snapshot

            parsed = json.loads(data)


            history.append(

                {

                    "id": snapshot_id,

                    "time": created_at,

                    "cpu": parsed["system"]["cpu_percent"],

                    "memory": parsed["system"]["memory_percent"],

                    "containers": parsed["docker"]["running"],

                    "health": parsed["health"],

                }

            )


        return history



    def get_latest_snapshot(self):


        snapshot = self.database.get_last_snapshot()


        if not snapshot:

            return None


        created_at, data = snapshot


        return {

            "created_at": created_at,

            "data": json.loads(data),

        }
