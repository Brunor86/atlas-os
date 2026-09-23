import subprocess



class DockerLogCollector:


    def __init__(
        self,
    ):

        pass



    def get_logs(
        self,
        container,
        lines=200,
    ):

        try:

            result = subprocess.run(

                [
                    "docker",
                    "logs",
                    "--tail",
                    str(lines),
                    container,
                ],

                capture_output=True,

                text=True,

            )


            output = result.stdout


            if result.stderr:

                output += "\n" + result.stderr



            return output.strip()



        except Exception:

            return None
