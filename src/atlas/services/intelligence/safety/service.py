from atlas.models.action import SafeAction


class ActionSafetyService:

    def evaluate(
        self,
        incident,
    ):

        recommendation = getattr(
            incident,
            "recommendation",
            {}
        )

        action = recommendation.get(
            "action"
        )

        incident_id = (
            getattr(
                incident,
                "incident_id",
                None,
            )
            or recommendation.get(
                "incident_id"
            )
            or ""
        )

        asset = getattr(
            incident,
            "asset",
            ""
        )

        target = str(
            recommendation.get(
                "target"
            )
            or asset
            or ""
        ).strip()

        if not action or action == "no recommendation":

            return {
                "status": "NO_ACTION",
                "reason": "no valid recommendation",
                "incident_id": incident_id,
            }


        #
        # Structured diagnosis safety rules.
        #
        # A failed SMART/storage health diagnosis means the
        # storage device must be inspected before allowing
        # disruptive recovery actions such as restart.
        #

        #
        # Diagnosis is propagated by IntelligenceOperator
        # through the temporary SafetyIncident object.
        #
        # Keep recommendation fallback for compatibility
        # with callers that still embed diagnosis there.
        #

        diagnosis = getattr(
            incident,
            "diagnosis",
            None,
        )

        if not isinstance(
            diagnosis,
            dict,
        ):
            diagnosis = recommendation.get(
                "diagnosis",
                {}
            )

        diagnosis_type = (
            diagnosis.get(
                "type"
            )
            if isinstance(
                diagnosis,
                dict,
            )
            else None
        )

        if (
            diagnosis_type
            == "STORAGE_HEALTH_FAILURE"
            and action in (
                "restart",
                "restart container",
                "stop container",
                "restart vm",
                "stop vm",
                "restart lxc",
                "stop lxc",
                "reboot",
                "shutdown",
            )
        ):

            return {
                "action": action,
                "target": target,
                "incident_id": incident_id,
                "risk": "CRITICAL",
                "requires_approval": False,
                "status": "BLOCKED",
                "reason": (
                    "storage health failure requires "
                    "diagnostic inspection before "
                    "disruptive action"
                ),
                "evidence": (
                    recommendation.get(
                        "evidence",
                        []
                    )
                ),
            }

        if action in (
            "start vm",
            "restart vm",
            "stop vm",
            "start lxc",
            "restart lxc",
            "stop lxc",
        ):

            verb, resource_type = (
                action.split(
                    " ",
                    1,
                )
            )

            risk = (
                "HIGH"
                if verb == "stop"
                else "MEDIUM"
            )

            rollback_action = (
                "stop"
                if verb == "start"
                else "start"
            )

            safe_action = SafeAction(
                action=action,
                target=target,
                incident_id=incident_id,
                risk=risk,
                requires_approval=True,
                rollback=(
                    rollback_action
                    + " "
                    + resource_type
                    + " "
                    + target
                ),
                status="PENDING_APPROVAL",
                evidence=(
                    recommendation.get(
                        "evidence",
                        []
                    )
                ),
            )

            result = (
                safe_action.__dict__
            )

            result["diagnosis"] = (
                diagnosis
            )

            result["safety"] = {
                "validated":
                    True,

                "risk":
                    risk,
            }

            return result


        if action == "start service":

            safe_action = SafeAction(
                action=action,
                target=target,
                incident_id=incident_id,
                risk="LOW",
                requires_approval=True,
                rollback=(
                    "systemctl stop "
                    + target
                ),
                status="PENDING_APPROVAL",
                evidence=(
                    recommendation.get(
                        "evidence",
                        []
                    )
                ),
            )

            result = safe_action.__dict__

            result["diagnosis"] = diagnosis

            result["safety"] = {
                "validated": True,
                "risk": "LOW",
            }

            return result


        if action == "restart service":

            safe_action = SafeAction(
                action=action,
                target=target,
                incident_id=incident_id,
                risk="LOW",
                requires_approval=True,
                rollback=(
                    "systemctl start "
                    + target
                ),
                status="PENDING_APPROVAL",
                evidence=(
                    recommendation.get(
                        "evidence",
                        []
                    )
                ),
            )

            result = safe_action.__dict__

            result["diagnosis"] = diagnosis

            result["safety"] = {
                "validated": True,
                "risk": "LOW",
            }

            return result


        if action == "stop service":

            safe_action = SafeAction(
                action=action,
                target=target,
                incident_id=incident_id,
                risk="MEDIUM",
                requires_approval=True,
                rollback=(
                    "systemctl start "
                    + target
                ),
                status="PENDING_APPROVAL",
                evidence=(
                    recommendation.get(
                        "evidence",
                        []
                    )
                ),
            )

            result = safe_action.__dict__

            result["diagnosis"] = diagnosis

            result["safety"] = {
                "validated": True,
                "risk": "MEDIUM",
            }

            return result


        if action == "start container":

            safe_action = SafeAction(
                action=action,

                target=target,

                incident_id=incident_id,

                risk="LOW",

                requires_approval=True,

                rollback=(
                    "docker stop "
                    + target
                ),

                status="PENDING_APPROVAL",

                evidence=(
                    recommendation.get(
                        "evidence",
                        []
                    )
                ),
            )

            result = safe_action.__dict__

            result["diagnosis"] = diagnosis

            result["safety"] = {
                "validated": True,
                "risk": "LOW",
            }

            return result


        if action == "stop container":

            safe_action = SafeAction(
                action=action,

                target=target,

                incident_id=incident_id,

                risk="MEDIUM",

                requires_approval=True,

                rollback=(
                    "docker start "
                    + target
                ),

                status="PENDING_APPROVAL",

                evidence=(
                    recommendation.get(
                        "evidence",
                        []
                    )
                ),
            )

            result = safe_action.__dict__

            result["diagnosis"] = diagnosis

            result["safety"] = {
                "validated": True,
                "risk": "MEDIUM",
            }

            return result


        if action == "restart container":

            safe_action = SafeAction(
                action=action,

                target=target,

                incident_id=incident_id,

                risk="LOW",

                requires_approval=True,

                rollback=(
                    "docker start "
                    + target
                ),

                status="PENDING_APPROVAL",

                evidence=(
                    recommendation.get(
                        "evidence",
                        []
                    )
                ),
            )

            result = safe_action.__dict__

            result["diagnosis"] = diagnosis

            result["safety"] = {
                "validated": True,
                "risk": "LOW",
            }

            return result

        #
        # Diagnostic / observational actions are safe to
        # propose but still require approval.
        #
        if action in (
            "inspect logs",
            "inspect temperature",
            "inspect",
            "check logs",
            "check temperature",
            "check health",
            "diagnose",
        ):

            return SafeAction(
                action=action,

                target=target,

                incident_id=incident_id,

                risk="LOW",

                requires_approval=True,

                status="PENDING_APPROVAL",

                evidence=(
                    recommendation.get(
                        "evidence",
                        []
                    )
                ),
            ).__dict__

        #
        # Unknown / unsupported actions are blocked by default.
        #
        return {
            "action": action,
            "target": target,
            "incident_id": incident_id,
            "risk": "UNKNOWN",
            "requires_approval": False,
            "status": "BLOCKED",
            "reason": (
                f"unsupported action: {action}"
            ),
            "evidence": recommendation.get(
                "evidence",
                [],
            ),
        }
