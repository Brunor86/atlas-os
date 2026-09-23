import subprocess


class DockerActionHandler:


    def start_container(
        self,
        container,
    ):

        if not container:

            return {
                "status": "FAILED",
                "result": "missing container",
                "evidence": [],
            }

        evidence = []

        try:

            start = subprocess.run(
                [
                    "docker",
                    "start",
                    container,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if start.returncode != 0:

                return {
                    "status": "FAILED",
                    "result": start.stderr.strip(),
                    "evidence": [],
                }

            evidence.append(
                f"docker start executed for {container}"
            )

            inspect = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "-f",
                    "{{.State.Running}}",
                    container,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if inspect.returncode != 0:

                return {
                    "status": "FAILED",
                    "result": inspect.stderr.strip(),
                    "evidence": evidence,
                }

            running = (
                inspect.stdout.strip().lower()
                == "true"
            )

            if not running:

                evidence.append(
                    "container is not running after start"
                )

                return {
                    "status": "FAILED",
                    "result": "container stopped after start",
                    "evidence": evidence,
                }

            evidence.append(
                "container running verification passed"
            )

            return {
                "status": "SUCCESS",
                "result": container,
                "evidence": evidence,
            }

        except Exception as exc:

            return {
                "status": "FAILED",
                "result": str(exc),
                "evidence": evidence,
            }


    def restart_container(
        self,
        container,
    ):

        if not container:

            return {

                "status": "FAILED",

                "result": "missing container",

                "evidence": []

            }


        evidence = []


        try:

            restart = subprocess.run(

                [
                    "docker",
                    "restart",
                    container,
                ],

                capture_output=True,

                text=True,

                timeout=30,

            )


            if restart.returncode != 0:

                return {

                    "status": "FAILED",

                    "result": restart.stderr.strip(),

                    "evidence": []

                }


            evidence.append(
                f"docker restart executed for {container}"
            )


            inspect = subprocess.run(

                [
                    "docker",
                    "inspect",
                    "-f",
                    "{{.State.Running}}",
                    container,
                ],

                capture_output=True,

                text=True,

                timeout=10,

            )


            if inspect.returncode != 0:

                return {

                    "status": "FAILED",

                    "result": inspect.stderr.strip(),

                    "evidence": evidence

                }


            running = (
                inspect.stdout.strip().lower()
                == "true"
            )


            if not running:

                evidence.append(
                    "container is not running after restart"
                )

                return {

                    "status": "FAILED",

                    "result": "container stopped after restart",

                    "evidence": evidence

                }


            evidence.append(
                "container running verification passed"
            )


            return {

                "status": "SUCCESS",

                "result": container,

                "evidence": evidence

            }


        except Exception as exc:

            return {

                "status": "FAILED",

                "result": str(exc),

                "evidence": evidence

            }

    def stop_container(
        self,
        container,
    ):

        if not container:

            return {
                "status": "FAILED",
                "result": "missing container",
                "evidence": [],
            }


        evidence = []


        try:

            stop = subprocess.run(
                [
                    "docker",
                    "stop",
                    container,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )


            if stop.returncode != 0:

                return {
                    "status": "FAILED",
                    "result": stop.stderr.strip(),
                    "evidence": [],
                }


            evidence.append(
                f"docker stop executed for {container}"
            )


            inspect = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "-f",
                    "{{.State.Running}}",
                    container,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )


            if inspect.returncode != 0:

                return {
                    "status": "FAILED",
                    "result": inspect.stderr.strip(),
                    "evidence": evidence,
                }


            running = (
                inspect.stdout.strip().lower()
                == "true"
            )


            if running:

                evidence.append(
                    "container is still running after stop"
                )

                return {
                    "status": "FAILED",
                    "result": "container running after stop",
                    "evidence": evidence,
                }


            evidence.append(
                "container stopped verification passed"
            )


            return {
                "status": "SUCCESS",
                "result": container,
                "evidence": evidence,
            }


        except Exception as exc:

            return {
                "status": "FAILED",
                "result": str(exc),
                "evidence": evidence,
            }
