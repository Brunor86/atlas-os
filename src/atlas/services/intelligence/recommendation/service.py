import json
from datetime import datetime, UTC

from atlas.models.action_plan import ActionPlan

from atlas.services.intelligence.learning.context import LearningContextService

from atlas.services.intelligence.memory.intelligence import (
    IncidentMemoryIntelligence
)


class ActionRecommendationService:


    def __init__(
        self,
        repository=None,
        asset_repository=None,
    ):

        self.repository = repository
        self.asset_repository = asset_repository

        self.learning_context = LearningContextService(
            repository
        )

        self.memory_intelligence = IncidentMemoryIntelligence(
            repository
        )



    def _operational_target(
        self,
        action_data,
    ):
        """
        Resolve the reasoning asset identifier into the
        canonical target accepted by the infrastructure
        executor.

        Explicit targets remain authoritative.

        If resolution fails, keep the specific asset_id
        rather than falling back to a broad target such as
        ``infrastructure``.
        """

        explicit = str(
            action_data.get(
                "target"
            )
            or ""
        ).strip()

        if explicit:
            return explicit

        asset_id = str(
            action_data.get(
                "asset_id"
            )
            or ""
        ).strip()

        if not asset_id:
            return "infrastructure"

        if self.asset_repository is None:
            return asset_id

        try:
            asset = (
                self.asset_repository
                .get_asset(
                    asset_id
                )
            )
        except Exception:
            asset = None

        if asset is None:
            return asset_id

        action = str(
            action_data.get(
                "action"
            )
            or ""
        ).strip().lower()

        metadata = (
            getattr(
                asset,
                "metadata",
                {},
            )
            or {}
        )

        candidate = None

        if action.endswith(
            "container"
        ):
            candidate = (
                metadata.get(
                    "container_name"
                )
                or getattr(
                    asset,
                    "name",
                    None,
                )
            )

        elif (
            action.endswith("vm")
            or action.endswith("lxc")
        ):
            identity = getattr(
                asset,
                "identity",
                None,
            )

            candidate = (
                getattr(
                    identity,
                    "serial",
                    None,
                )
                or getattr(
                    asset,
                    "name",
                    None,
                )
            )

        else:
            candidate = getattr(
                asset,
                "name",
                None,
            )

        return str(
            candidate
            or asset_id
        ).strip()


    def recommend(
        self,
        incident,
    ):

        history = self.get_history(
            incident
        )


        learning = self.learning_context.get_context(
            incident
        )


        memory_intelligence = self.memory_intelligence.analyze(
            incident
        )


        actions = []

        evidence = []

        incident_id = ""

        #
        # prefer successful actions from operational memory
        #

        learned_actions = memory_intelligence.get(
            "successful_actions",
            []
        )


        if learned_actions:

            actions.extend(
                learned_actions
            )


            evidence.append(
                {
                    "source": "memory_intelligence",
                    "successful_actions": learned_actions,
                }
            )




        for item in history:

            if isinstance(
                item,
                (list, tuple)
            ):

                evidence.append(
                    item[0]
                )



                if len(item) > 4:

                    try:

                        previous_actions = json.loads(
                            item[4]
                        )

                    except (
                        json.JSONDecodeError,
                        TypeError,
                    ):

                        previous_actions = []


                    actions.extend(
                        previous_actions
                    )



        if actions:

            action = actions[0]

            status = "recommended"

            confidence = 0.85

            reason = [
                "previous incidents contain successful actions"
            ]


            if learning["similar_cases"] > 0:

                confidence = max(
                    confidence,
                    learning["confidence"]
                )


                reason.append(
                    f"{learning['similar_cases']} similar learning case(s) found"
                )


                evidence.extend(
                    learning["evidence"]
                )

        else:


            if learning["similar_cases"] > 0 and learning.get(
                "recommended_action"
            ):

                return {

                    "action": learning["recommended_action"],

                    "status": "learning_recommended",

                    "confidence": learning["confidence"],

                    "reason": [

                        f"{learning['similar_cases']} similar incidents solved successfully"

                    ],

                    "evidence": learning["evidence"],

                    "generated_at": datetime.now(UTC).isoformat(),

                }



            fallback_actions = {

                "container failure":
                    "restart container",

                "container stopped":
                    "restart container",

                "prometheus":
                    "restart container",

            }


            action = None


            context = (
                incident.name
                + " "
                + incident.reason
            ).lower()


            for key, value in fallback_actions.items():

                if key in context:

                    action = value

                    break


            if action:

                status = "fallback_recommended"

                confidence = 0.7

                reason = [

                    "fallback action from operational rule"

                ]

            else:

                status = "insufficient_history"

                confidence = 0.2

                reason = [

                    "no historical action found"

                ]



        return {

            "action": action,

            "status": status,

            "confidence": confidence,

            "reason": reason,

            "evidence": evidence,

            "generated_at": datetime.now(UTC).isoformat(),

        }



    def _select_reasoning_action(
        self,
        actions,
    ):
        """
        Preserve Reasoner ordering while allowing a concrete
        operational action to refine a generic ``<verb> asset``
        action for the same asset.

        The recommendation layer does not invent resource types.
        It only prefers a specific action that the Reasoner
        already produced.
        """

        if not actions:
            return None

        selected = actions[0]

        if not isinstance(
            selected,
            dict,
        ):
            return selected

        selected_action = str(
            selected.get(
                "action"
            )
            or ""
        ).strip().lower()

        #
        # Concrete actions remain authoritative.
        #
        if not selected_action.endswith(
            " asset"
        ):
            return selected

        parts = selected_action.split(
            maxsplit=1
        )

        if len(parts) != 2:
            return selected

        verb = parts[0]

        selected_asset_id = str(
            selected.get(
                "asset_id"
            )
            or ""
        ).strip()

        if not selected_asset_id:
            return selected

        for candidate in actions[1:]:

            if not isinstance(
                candidate,
                dict,
            ):
                continue

            candidate_action = str(
                candidate.get(
                    "action"
                )
                or ""
            ).strip().lower()

            candidate_asset_id = str(
                candidate.get(
                    "asset_id"
                )
                or ""
            ).strip()

            if (
                not candidate_action
                or candidate_asset_id
                != selected_asset_id
            ):
                continue

            candidate_parts = (
                candidate_action.split(
                    maxsplit=1
                )
            )

            if (
                len(candidate_parts)
                != 2
                or candidate_parts[0]
                != verb
            ):
                continue

            #
            # A second generic action does not refine anything.
            #
            if candidate_action.endswith(
                " asset"
            ):
                continue

            return candidate

        return selected


    def recommend_from_reasoning(
        self,
        reasoning,
        incident_id=None,
        memory=None,
    ):

        actions = reasoning.get(
            "recommended_actions",
            []
        )

        #
        # No action produced by the reasoning engine.
        #
        # Keep the existing dictionary contract for
        # callers that explicitly inspect the empty state.
        #
        if not actions:

            return None

        #
        # The reasoner is the authoritative source
        # for the immediate operational action.
        #
        action_data = (
            self._select_reasoning_action(
                actions
            )
        )

        if not isinstance(
            action_data,
            dict,
        ):
            return None

        action = action_data.get(
            "action"
        )

        if not action:

            return None

        confidence = action_data.get(
            "confidence",
            0.9,
        )

        reasons = []

        reason = action_data.get(
            "reason"
        )

        if reason:
            if isinstance(
                reason,
                list,
            ):
                reasons.extend(
                    reason
                )
            else:
                reasons.append(
                    reason
                )

        #
        # Structured diagnosis generated by the reasoner.
        #
        diagnosis = reasoning.get(
            "diagnosis"
        )

        if diagnosis:

            diagnosis_summary = diagnosis.get(
                "summary"
            )

            if diagnosis_summary:

                reasons.append(
                    diagnosis_summary
                )

        #
        # Preserve structured evidence.
        #
        evidence = []

        action_evidence = action_data.get(
            "evidence"
        )

        if action_evidence:

            if isinstance(
                action_evidence,
                list,
            ):

                for item in action_evidence:

                    if isinstance(
                        item,
                        dict,
                    ):

                        evidence.append(
                            dict(item)
                        )

            elif isinstance(
                action_evidence,
                dict,
            ):

                evidence.append(
                    dict(action_evidence)
                )

        #
        # Preserve reasoning-level evidence.
        #
        reasoning_evidence = reasoning.get(
            "evidence",
            []
        )

        if reasoning_evidence:

            if isinstance(
                reasoning_evidence,
                list,
            ):

                for item in reasoning_evidence:

                    if isinstance(
                        item,
                        dict,
                    ):

                        evidence.append(
                            dict(item)
                        )

            elif isinstance(
                reasoning_evidence,
                dict,
            ):

                evidence.append(
                    dict(reasoning_evidence)
                )

        #
        # Preserve diagnosis evidence when present.
        #
        if diagnosis:

            diagnosis_evidence = diagnosis.get(
                "evidence"
            )

            if diagnosis_evidence:

                if isinstance(
                    diagnosis_evidence,
                    dict,
                ):

                    evidence.append(
                        {
                            "source": "diagnosis",
                            "observation": dict(
                                diagnosis_evidence
                            ),
                        }
                    )

                elif isinstance(
                    diagnosis_evidence,
                    list,
                ):

                    for item in diagnosis_evidence:

                        if isinstance(
                            item,
                            dict,
                        ):

                            evidence.append(
                                {
                                    "source": "diagnosis",
                                    "observation": dict(
                                        item
                                    ),
                                }
                            )

        #
        # Historical memory can increase confidence
        # and contribute supporting evidence.
        #
        if memory:

            matches = memory.get(
                "matches",
                memory.get(
                    "similar_cases",
                    0,
                ),
            )

            if matches > 0:

                confidence = min(
                    confidence + 0.05,
                    1.0,
                )

                reasons.append(
                    f"{matches} similar historical incident(s) found"
                )

                memory_evidence = memory.get(
                    "evidence",
                    []
                )

                if memory_evidence:

                    if isinstance(
                        memory_evidence,
                        list,
                    ):

                        evidence.extend(
                            memory_evidence
                        )

                    else:

                        evidence.append(
                            memory_evidence
                        )

                    #
                    # Preserve the historical incident
                    # identifier when available.
                    #
                    first_evidence = (
                        memory_evidence[0]
                        if isinstance(
                            memory_evidence,
                            list,
                        )
                        and memory_evidence
                        else memory_evidence
                    )

                    if isinstance(
                        first_evidence,
                        dict,
                    ):

                        historical_incident = (
                            first_evidence.get(
                                "incident"
                            )
                        )

                        if (
                            historical_incident
                            and isinstance(
                                historical_incident,
                                (list, tuple),
                            )
                            and historical_incident
                        ):

                            incident_id = (
                                incident_id
                                or historical_incident[0]
                            )

        #
        # Remove duplicated evidence while preserving
        # insertion order.
        #
        unique_evidence = []

        seen_evidence = set()

        for item in evidence:

            try:
                key = repr(item)
            except Exception:
                key = str(item)

            if key in seen_evidence:
                continue

            seen_evidence.add(key)

            unique_evidence.append(
                item
            )

        evidence = unique_evidence

        #
        # Operational defaults.
        #
        risk = action_data.get(
            "risk",
            "UNKNOWN",
        )

        target = (
            self._operational_target(
                action_data
            )
        )

        prerequisites = action_data.get(
            "prerequisites",
            [],
        )

        rollback = action_data.get(
            "rollback",
            "",
        )

        #
        # Build the domain ActionPlan.
        #
        return ActionPlan(

            action=action,

            target=target,

            incident_id=(
                incident_id
                or action_data.get(
                    "incident_id",
                    "",
                )
            ),

            reason=reasons,

            evidence=evidence,

            risk=risk,

            prerequisites=prerequisites,

            rollback=rollback,

            confidence=confidence,

        )
