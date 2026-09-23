class IntelligenceReasoner:

    def reason(
        self,
        insights,
        context,
        dependency=None,
        asset_context=None,
    ):

        reasoning = []
        risks = []
        actions = []

        #
        # Asset-aware reasoning
        #

        if asset_context:

            asset = asset_context.get(
                "asset",
                {}
            )

            identity = asset_context.get(
                "identity",
                {}
            )

            name = asset.get(
                "name",
                "unknown"
            )

            status = asset.get(
                "status",
                "UNKNOWN"
            )

            health = asset.get(
                "health",
                0
            )

            roles = asset.get(
                "roles",
                []
            )

            capabilities = asset.get(
                "capabilities",
                []
            )

            reasoning.append(
                f"Incident associated with asset: {name}"
            )

            reasoning.append(
                f"Asset status: {status}"
            )

            reasoning.append(
                f"Asset health: {health}"
            )

            if roles:

                reasoning.append(
                    "Asset roles: "
                    + ", ".join(roles)
                )

            if capabilities:

                reasoning.append(
                    "Available asset capabilities: "
                    + ", ".join(capabilities)
                )

            vendor = identity.get(
                "vendor"
            )

            model = identity.get(
                "model"
            )

            if vendor or model:

                identity_text = " / ".join(
                    value
                    for value in (
                        vendor,
                        model,
                    )
                    if value
                )

                reasoning.append(
                    f"Asset identity: {identity_text}"
                )

            #
            # Availability takes precedence
            #

            if status == "OFFLINE":

                risks.append(
                    f"Asset {name} is offline"
                )

                risks.append(
                    "service interruption possible"
                )

                if "RESTART" in capabilities:

                    actions.append(
                        {
                            "action": "restart asset",
                            "reason": (
                                f"Asset {name} is offline "
                                "and supports restart"
                            ),
                            "risk": "MEDIUM",
                            "asset_id": asset.get(
                                "id"
                            ),
                        }
                    )

                elif "START" in capabilities:

                    actions.append(
                        {
                            "action": "start asset",
                            "reason": (
                                f"Asset {name} is offline "
                                "and supports start"
                            ),
                            "risk": "MEDIUM",
                            "asset_id": asset.get(
                                "id"
                            ),
                        }
                    )

            #
            # Online but degraded
            #

            elif status == "ONLINE" and health < 90:

                risks.append(
                    f"Asset {name} has degraded health"
                )

                if "LOGS" in capabilities:

                    actions.append(
                        {
                            "action": "inspect asset logs",
                            "reason": (
                                f"Asset {name} has degraded health "
                                "and supports log inspection"
                            ),
                            "risk": "LOW",
                            "asset_id": asset.get(
                                "id"
                            ),
                        }
                    )

            #
            # Unknown state
            #

            elif status not in (
                "ONLINE",
                "OFFLINE",
            ):

                risks.append(
                    f"Asset {name} has unknown availability"
                )

        #
        # Observation-aware reasoning
        #
        # Observations are direct evidence associated with
        # the incident asset. Their severity can influence
        # both reasoning and final state.
        #

        if asset_context:

            observations = asset_context.get(
                "observations",
                []
            )

            asset = asset_context.get(
                "asset",
                {}
            )

            name = asset.get(
                "name",
                "unknown"
            )

            capabilities = asset.get(
                "capabilities",
                []
            )

            has_critical_observation = False
            has_warning_observation = False

            diagnoses = []

            for observation in observations:

                observation_type = observation.get(
                    "type",
                    "unknown"
                )

                value = observation.get(
                    "value",
                    ""
                )

                severity = str(
                    observation.get(
                        "severity",
                        "INFO"
                    )
                ).upper()

                source = observation.get(
                    "source",
                    "unknown"
                )

                #
                # Deterministic diagnosis classification.
                #
                # Observations are converted into a small,
                # structured diagnostic vocabulary so later
                # reasoning/AI stages do not have to infer
                # the basic meaning from raw text.
                #

                diagnosis_type = None
                diagnosis_category = None
                diagnosis_confidence = 0.0

                if observation_type.lower() == "dns":

                    value_text = str(
                        value
                    ).lower()

                    if (
                        "resolution failed"
                        in value_text
                        or "dns"
                        in value_text
                    ):

                        diagnosis_type = (
                            "DNS_FAILURE"
                        )

                        diagnosis_category = (
                            "NETWORK"
                        )

                        diagnosis_confidence = 0.95

                elif observation_type.lower() == "smart":

                    value_text = str(
                        value
                    ).upper()

                    if value_text == "FAILED":

                        diagnosis_type = (
                            "STORAGE_HEALTH_FAILURE"
                        )

                        diagnosis_category = (
                            "STORAGE"
                        )

                        diagnosis_confidence = 0.98

                elif observation_type.lower() == "temperature":

                    diagnosis_type = (
                        "HIGH_TEMPERATURE"
                    )

                    diagnosis_category = (
                        "THERMAL"
                    )

                    diagnosis_confidence = 0.80

                if diagnosis_type:

                    diagnoses.append(
                        {
                            "type": diagnosis_type,
                            "category": diagnosis_category,
                            "confidence": (
                                diagnosis_confidence
                            ),
                            "evidence": {
                                "observation_type":
                                    observation_type,
                                "value":
                                    value,
                                "severity":
                                    severity,
                                "source":
                                    source,
                            },
                        }
                    )

                reasoning.append(
                    f"Asset observation: "
                    f"{observation_type}={value} "
                    f"(severity={severity}, source={source})"
                )

                if severity == "CRITICAL":

                    has_critical_observation = True

                    risks.append(
                        f"Asset {name} has critical "
                        f"{observation_type} observation"
                    )

                elif severity == "WARNING":

                    has_warning_observation = True

                    risks.append(
                        f"Asset {name} has warning "
                        f"{observation_type} observation"
                    )

                #
                # Critical evidence should be diagnosed
                # before attempting a disruptive action.
                #

                if severity in (
                    "WARNING",
                    "CRITICAL",
                ) and "LOGS" in capabilities:

                    actions.append(
                        {
                            "action": "inspect logs",
                            "reason": (
                                f"Investigate {observation_type} "
                                f"observation for asset {name}"
                            ),
                            "risk": "LOW",
                            "asset_id": asset.get(
                                "id"
                            ),
                            "evidence": {
                                "type": observation_type,
                                "value": value,
                                "severity": severity,
                                "source": source,
                            },
                        }
                    )

            #
            # Observation severity contributes to state.
            #

            if has_critical_observation:

                state_from_observations = "CRITICAL"

            elif has_warning_observation:

                state_from_observations = "WARNING"

            else:

                state_from_observations = "HEALTHY"

        else:

            state_from_observations = "HEALTHY"

        #
        # Deterministic insights
        #

        for insight in insights:

            title = insight.get(
                "title",
                ""
            )

            title_lower = title.lower()

            #
            # CPU
            #

            if "cpu" in title_lower:

                reasoning.append(
                    "High CPU condition detected"
                )

                risks.append(
                    "possible service degradation"
                )

                actions.append(
                    {
                        "action": "inspect services",
                        "reason": (
                            "CPU saturation detected"
                        ),
                        "risk": "LOW",
                    }
                )

            #
            # Memory
            #

            if "memory" in title_lower:

                reasoning.append(
                    "Memory pressure detected"
                )

                risks.append(
                    "possible resource exhaustion"
                )

                actions.append(
                    {
                        "action": "analyze memory consumers",
                        "reason": (
                            "memory usage increasing"
                        ),
                        "risk": "LOW",
                    }
                )

            #
            # Docker container stopped
            #

            if "container stopped" in title_lower:

                reasoning.append(
                    "Docker container availability issue detected"
                )

                risks.append(
                    "service interruption possible"
                )

                actions.append(
                    {
                        "action": "restart container",
                        "reason": insight.get(
                            "message",
                            "Docker container is stopped",
                        ),
                        "risk": "MEDIUM",
                        "asset_id": insight.get(
                            "asset_id"
                        ),
                    }
                )

        #
        # Context health
        #

        health_state = context.get(
            "health",
            "healthy"
        )

        if health_state != "healthy":

            reasoning.append(
                f"Infrastructure health state: {health_state}"
            )

            risks.append(
                "Infrastructure degradation detected"
            )

        #
        # Alerts reasoning
        #

        for alert in context.get(
            "alerts",
            []
        ):

            source = alert.get(
                "source",
                ""
            )

            if source == "docker":

                reasoning.append(
                    "Docker container availability issue detected"
                )

                risks.append(
                    "service interruption possible"
                )

                actions.append(
                    {
                        "action": "inspect stopped containers",
                        "reason": alert.get(
                            "message",
                            ""
                        ),
                        "risk": "LOW",
                    }
                )

        #
        # Dependency impact reasoning
        #

        if dependency:

            dependency_severity = dependency.get(
                "severity",
                "UNKNOWN"
            )

            upstream = dependency.get(
                "upstream",
                []
            )

            downstream = dependency.get(
                "downstream",
                []
            )

            affected = dependency.get(
                "affected",
                []
            )

            if dependency_severity == "HIGH":

                reasoning.append(
                    "High dependency impact detected"
                )

                risks.append(
                    "multiple infrastructure assets may be affected"
                )

            elif dependency_severity == "MEDIUM":

                reasoning.append(
                    "Dependency impact detected"
                )

                risks.append(
                    "dependent infrastructure assets may be affected"
                )

            if upstream:

                reasoning.append(
                    "Upstream dependency detected: "
                    + ", ".join(upstream)
                )

            if downstream:

                reasoning.append(
                    "Downstream dependency detected: "
                    + ", ".join(downstream)
                )

            if affected:

                reasoning.append(
                    f"{len(affected)} affected asset(s) identified"
                )

        #
        # State
        #

        state = "HEALTHY"

        #
        # Observation severity is direct evidence and
        # therefore takes precedence over descriptive
        # reasoning.
        #

        if state_from_observations == "CRITICAL":

            state = "CRITICAL"

        elif state_from_observations == "WARNING":

            state = "WARNING"

        #
        # Asset health is authoritative when an
        # incident is associated with an asset.
        #
        # Descriptive reasoning must not by itself
        # downgrade a healthy asset to WARNING.
        #

        if asset_context:

            asset = asset_context.get(
                "asset",
                {}
            )

            status = asset.get(
                "status",
                "UNKNOWN"
            )

            health = asset.get(
                "health",
                0
            )

            if status == "OFFLINE":

                state = "CRITICAL"

            elif (
                status == "ONLINE"
                and health < 90
            ):

                state = "WARNING"

            elif status not in (
                "ONLINE",
                "OFFLINE",
            ):

                state = "WARNING"

        elif risks or reasoning:

            state = "WARNING"

        if dependency:

            if dependency.get(
                "severity"
            ) == "HIGH":

                state = "CRITICAL"

        #
        # Deduplicate actions
        #

        unique_actions = []

        seen_actions = set()

        for action in actions:

            action_name = (
                action.get(
                    "action",
                    ""
                )
                .strip()
                .lower()
            )

            asset_id = action.get(
                "asset_id"
            )

            #
            # Semantic equivalence for log inspection.
            #
            # Different reasoning stages may describe the
            # same diagnostic action differently:
            #
            #   "inspect asset logs"
            #   "inspect logs"
            #
            # They should result in one operator action.
            #

            normalized_action = action_name

            if action_name in (
                "inspect asset logs",
                "inspect logs",
            ):

                normalized_action = "inspect logs"

            key = (
                normalized_action,
                asset_id,
            )

            if key in seen_actions:

                #
                # Prefer a specific observation-driven
                # log inspection over the generic degraded
                # health log inspection.
                #

                if normalized_action == "inspect logs":

                    for index, existing in enumerate(
                        unique_actions
                    ):

                        existing_action = existing.get(
                            "action"
                        )

                        if (
                            existing_action
                            == "inspect asset logs"
                            and existing.get("asset_id")
                            == asset_id
                        ):

                            unique_actions[index] = action

                            break

                continue

            seen_actions.add(key)

            unique_actions.append(
                action
            )

        return {

            "state": state,

            "reasoning": reasoning,

            "risks": risks,

            "recommended_actions": unique_actions,

            "diagnoses": (
                diagnoses
                if asset_context
                else []
            ),

        }
