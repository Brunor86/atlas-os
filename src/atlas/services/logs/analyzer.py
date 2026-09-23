class LogAnalyzer:


    def analyze(
        self,
        logs,
        container=None,
    ):


        if not logs:

            return {

                "severity": "UNKNOWN",

                "category": "unknown",

                "pattern": None,

                "confidence": 0.0,

                "message": "No logs available",

            }



        text = logs.lower()



        health = None


        if container:

            health = container.get(
                "health"
            )



        critical_patterns = {


            "out_of_memory":

                [
                    "out of memory",
                    "oom",
                ],



            "connection_failure":

                [
                    "connection refused",
                    "failed to connect",
                ],



            "startup_failure":

                [
                    "cannot start",
                    "unable to start",
                ],

        }



        for name, patterns in critical_patterns.items():


            for pattern in patterns:


                if pattern in text:


                    return {

                        "severity":
                            "HIGH",

                        "category":
                            "error",

                        "pattern":
                            name,

                        "confidence":
                            0.95,

                        "message":
                            f"Detected critical log pattern: {name}",

                    }




        exception_details = {


            "exception":

                text.count(
                    "exception"
                ),


            "traceback":

                text.count(
                    "traceback"
                ),


            "fatal":

                text.count(
                    "fatal"
                ),

        }



        total_exceptions = sum(
            exception_details.values()
        )



        if total_exceptions >= 5:


            return {


                "severity":
                    "HIGH",


                "category":
                    "error",


                "pattern":
                    "repeated_exception",


                "count":
                    total_exceptions,


                "details":
                    exception_details,


                "confidence":
                    min(
                        0.95,
                        0.70 +
                        (
                            total_exceptions * 0.02
                        )
                    ),


                "message":
                    f"Detected repeated exceptions ({total_exceptions})",

            }





        if total_exceptions > 0:


            if health == "healthy":


                return {


                    "severity":
                        "LOW",


                    "category":
                        "handled_exception",


                    "pattern":
                        "exception",


                    "count":
                        total_exceptions,


                    "details":
                        exception_details,


                    "confidence":
                        0.75,


                    "message":
                        "Exception detected but container is healthy",

                }



            return {


                "severity":
                    "MEDIUM",


                "category":
                    "warning",


                "pattern":
                    "exception",


                "count":
                    total_exceptions,


                "details":
                    exception_details,


                "confidence":
                    0.65,


                "message":
                    "Exception detected",

            }





        warning_patterns = {


            "timeout":

                [
                    "timeout",
                    "timed out",
                ],


            "warning":

                [
                    "warning",
                    "deprecated",
                ],

        }



        for name, patterns in warning_patterns.items():


            for pattern in patterns:


                if pattern in text:


                    return {


                        "severity":
                            "MEDIUM",


                        "category":
                            "warning",


                        "pattern":
                            name,


                        "confidence":
                            0.55,


                        "message":
                            f"Detected warning pattern: {name}",

                    }





        graceful_patterns = {


            "graceful_stop":

                [
                    "sigterm",
                    "stopping",
                    "shutdown complete",
                ],

        }



        for name, patterns in graceful_patterns.items():


            for pattern in patterns:


                if pattern in text:


                    return {


                        "severity":
                            "INFO",


                        "category":
                            "lifecycle",


                        "pattern":
                            name,


                        "confidence":
                            0.90,


                        "message":
                            "Container stopped gracefully",

                    }





        return {


            "severity":
                "INFO",


            "category":
                "normal",


            "pattern":
                None,


            "confidence":
                0.90,


            "message":
                "No relevant issues detected",

        }
