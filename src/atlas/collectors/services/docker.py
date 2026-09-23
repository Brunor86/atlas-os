from dataclasses import dataclass

import json
import subprocess

from atlas.collectors.base import Collector


@dataclass(slots=True)
class DockerServiceInfo:

    id: str

    name: str

    image: str

    status: str

    state: str

    ports: str



class DockerServiceCollector(Collector):

    name = "docker-services"


    def collect(self):

        result = subprocess.run(

            [

                "docker",

                "ps",

                "-a",

                "--format",

                "{{json .}}",

            ],

            capture_output=True,

            text=True,

        )


        services = []


        for line in result.stdout.splitlines():

            if not line.strip():

                continue


            row = json.loads(line)


            services.append(

                DockerServiceInfo(

                    id=row["ID"],

                    name=row["Names"],

                    image=row["Image"],

                    status=row["Status"],

                    state=row.get(
                        "State",
                        ""
                    ),

                    ports=row["Ports"],

                )

            )


        return services
