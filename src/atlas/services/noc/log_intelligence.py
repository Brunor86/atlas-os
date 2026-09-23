from atlas.services.logs.manager import LogManager



class NOCLogIntelligence:


    def __init__(self):

        self.manager = LogManager()



    def analyze(
        self,
        containers=None,
    ):

        if not containers:

            return []



        results = self.manager.analyze_containers(
            containers
        )


        findings = []



        for item in results:


            analysis = item.get(
                "analysis",
                {}
            )


            if not analysis:

                continue



            findings.append(

                {

                    "service":
                        item.get(
                            "container",
                            "unknown"
                        ),


                    "pattern":
                        analysis.get(
                            "pattern"
                        ),


                    "severity":
                        analysis.get(
                            "severity"
                        ),

                    "criticality":
                        item.get(
                            "criticality",
                            "MEDIUM",
                        ),


                    "confidence":
                        analysis.get(
                            "confidence",
                            0
                        ),


                    "message":
                        analysis.get(
                            "message",
                            ""
                        ),

                }

            )


        return findings
