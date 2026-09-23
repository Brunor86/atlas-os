class ChangeDetector:


    def analyze(
        self,
        git_context,
    ):

        status = git_context.get(
            "status",
            ""
        )


        last_commit = git_context.get(
            "last_commit",
            ""
        )


        changes = []


        if status:

            for line in status.splitlines():

                parts = line.strip().split(
                    " ",
                    1
                )

                if len(parts) == 2:

                    changes.append(
                        parts[1]
                    )


        risk = "LOW"


        if any(
            "docker" in file.lower()
            or "compose" in file.lower()
            for file in changes
        ):

            risk = "HIGH"


        elif changes:

            risk = "MEDIUM"



        return {

            "changes_detected":
                bool(changes),


            "last_commit":
                last_commit,


            "files_changed":
                changes,


            "risk":
                risk,

        }
