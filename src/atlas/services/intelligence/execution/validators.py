class ActionValidator:


    ALLOWED_ACTIONS = [

        "restart container",

        "start container",

        "stop container",

        "start service",

        "restart service",

        "stop service",

        "start vm",

        "stop vm",

        "restart vm",

        "restart lxc",

        "inspect stopped containers",

    ]


    def validate(
        self,
        action,
    ):

        if not action:

            return {

                "valid": False,

                "reason": "empty action"

            }


        if action not in self.ALLOWED_ACTIONS:

            return {

                "valid": False,

                "reason": "action not allowed"

            }


        return {

            "valid": True,

            "reason": "action approved by policy"

        }
