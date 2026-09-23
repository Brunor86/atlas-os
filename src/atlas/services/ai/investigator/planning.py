from __future__ import annotations

from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    computed_field,
    field_validator,
    model_validator,
)

from atlas.core.asset import (
    AssetRole,
    AssetStatus,
    AssetType,
    Criticality,
)

from atlas.services.ai.investigator.scope import (
    EvidenceDomain,
    InvestigationScope,
    InvestigationScopeMode,
)


class InvestigationDirection(StrEnum):

    UPSTREAM = "UPSTREAM"

    DOWNSTREAM = "DOWNSTREAM"


class RelationAnchor(StrEnum):
    """
    Position occupied by the investigation target in the canonical
    relationship:

        SUBJECT --RELATIONSHIP--> OBJECT

    The LLM identifies the semantic anchor.

    ATLAS derives graph traversal direction deterministically.
    """

    SUBJECT = "SUBJECT"

    OBJECT = "OBJECT"


class InvestigationPlan(BaseModel):
    """
    Semantic plan produced before evidence collection.

    The plan describes what must be investigated.

    It does not contain infrastructure facts and it does not
    authorize any evidence by itself.

    For relationship investigations, the planner identifies the
    target's semantic position in the canonical relationship.
    Traversal direction is derived deterministically by ATLAS.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    domain: EvidenceDomain

    scope_mode: InvestigationScopeMode

    target_query: str | None = None

    collection_query: str | None = None

    relationship: str | None = None

    relation_anchor: RelationAnchor | None = None

    observation: str | None = None

    # Canonical ATLAS inventory selectors used by STATUS
    # investigations.
    #
    # collection_query remains human-readable planning intent.
    # These fields are the deterministic operational selectors.
    asset_type: str | None = None

    role: str | None = None

    criticality: str | None = None

    status_filter: str | None = None


    @model_validator(
        mode="before"
    )
    @classmethod
    def migrate_legacy_scope_input(
        cls,
        value,
    ):
        """
        Compatibility boundary for deterministic callers.

        global_scope is accepted from legacy Python construction
        but is not part of the canonical planner input schema.
        """

        if not isinstance(
            value,
            dict,
        ):

            return value

        data = dict(
            value
        )

        legacy_global = data.pop(
            "global_scope",
            None,
        )

        if (
            "scope_mode"
            not in data
        ):

            if legacy_global is True:

                data[
                    "scope_mode"
                ] = (
                    InvestigationScopeMode
                    .GLOBAL
                )

            elif data.get(
                "collection_query"
            ):

                data[
                    "scope_mode"
                ] = (
                    InvestigationScopeMode
                    .COLLECTION
                )

            else:

                data[
                    "scope_mode"
                ] = (
                    InvestigationScopeMode
                    .TARGET
                )

        return data


    @computed_field
    @property
    def global_scope(
        self,
    ) -> bool:

        return (
            self.scope_mode
            == InvestigationScopeMode.GLOBAL
        )


    @computed_field
    @property
    def direction(
        self,
    ) -> InvestigationDirection | None:
        """
        Deterministic graph traversal derived from the target's
        position in the canonical relationship.

        SUBJECT --RELATIONSHIP--> OBJECT

        If the investigation target is SUBJECT, traverse outgoing
        edges to discover what it points to: DOWNSTREAM.

        If the investigation target is OBJECT, traverse incoming
        edges to discover what points to it: UPSTREAM.
        """

        if (
            self.domain
            != EvidenceDomain.RELATION
        ):

            return None

        if (
            self.relation_anchor
            == RelationAnchor.SUBJECT
        ):

            return (
                InvestigationDirection
                .DOWNSTREAM
            )

        if (
            self.relation_anchor
            == RelationAnchor.OBJECT
        ):

            return (
                InvestigationDirection
                .UPSTREAM
            )

        return None


    @field_validator(
        "target_query"
    )
    @classmethod
    def normalize_target_query(
        cls,
        value,
    ):

        if value is None:
            return None

        normalized = str(
            value
        ).strip()

        return normalized or None


    @field_validator(
        "collection_query"
    )
    @classmethod
    def normalize_collection_query(
        cls,
        value,
    ):

        if value is None:
            return None

        normalized = str(
            value
        ).strip()

        return normalized or None


    @field_validator(
        "relationship"
    )
    @classmethod
    def normalize_relationship(
        cls,
        value,
    ):

        if value is None:
            return None

        normalized = str(
            value
        ).strip().upper()

        return normalized or None


    @field_validator(
        "observation"
    )
    @classmethod
    def normalize_observation(
        cls,
        value,
    ):

        if value is None:
            return None

        normalized = str(
            value
        ).strip()

        return normalized or None


    @field_validator(
        "asset_type",
        "role",
        "criticality",
        "status_filter",
    )
    @classmethod
    def normalize_status_selector(
        cls,
        value,
    ):

        if value is None:
            return None

        normalized = str(
            value
        ).strip().upper()

        return normalized or None


    @model_validator(
        mode="after"
    )
    def validate_plan(
        self,
    ):

        # ----------------------------------------------------------
        # Canonical semantic scope.
        # ----------------------------------------------------------

        if (
            self.scope_mode
            == InvestigationScopeMode.GLOBAL
        ):

            self.target_query = None
            self.collection_query = None

        elif (
            self.scope_mode
            == InvestigationScopeMode.COLLECTION
        ):

            self.target_query = None

            if (
                self.domain
                != EvidenceDomain.UNKNOWN
                and not self.collection_query
            ):

                raise ValueError(
                    "COLLECTION investigation "
                    "requires collection_query."
                )

        else:

            self.collection_query = None

        if (
            self.domain
            == EvidenceDomain.RELATION
        ):

            if (
                self.scope_mode
                != InvestigationScopeMode.TARGET
            ):

                raise ValueError(
                    "RELATION investigation "
                    "requires TARGET scope."
                )

            if not self.target_query:

                raise ValueError(
                    "RELATION investigation "
                    "requires target_query."
                )

            if not self.relationship:

                raise ValueError(
                    "RELATION investigation "
                    "requires relationship."
                )

            if (
                self.relation_anchor
                is None
            ):

                raise ValueError(
                    "RELATION investigation "
                    "requires relation_anchor."
                )

        else:

            # Relationship-specific fields have no semantic meaning
            # outside RELATION investigations.
            #
            # Structured-output models may populate optional fields
            # even when they are irrelevant to the selected domain.
            # ATLAS canonicalizes that noise instead of allowing it
            # to alter investigation semantics or exhaust retries.
            self.relationship = None
            self.relation_anchor = None

        if (
            self.domain
            == EvidenceDomain.OBSERVATION
        ):

            if not self.observation:

                raise ValueError(
                    "OBSERVATION investigation "
                    "requires observation."
                )

        else:

            # Observation intent is meaningful only for telemetry /
            # measured-value investigations.
            self.observation = None

        # ----------------------------------------------------------
        # Canonical STATUS selectors.
        #
        # Human-readable collection_query is planning traceability.
        # Actual inventory selection must use canonical ATLAS
        # ontology dimensions.
        # ----------------------------------------------------------

        if (
            self.domain
            == EvidenceDomain.STATUS
        ):

            if (
                self.scope_mode
                == InvestigationScopeMode.TARGET
            ):

                # TARGET asks for the actual current state of one
                # resolved entity. Filtering by an expected state
                # could hide the opposite answer.
                self.asset_type = None
                self.role = None
                self.criticality = None
                self.status_filter = None

            elif (
                self.scope_mode
                == InvestigationScopeMode.GLOBAL
            ):

                # GLOBAL covers the whole inventory. Only a desired
                # status condition may narrow the result.
                self.asset_type = None
                self.role = None
                self.criticality = None

            elif (
                self.scope_mode
                == InvestigationScopeMode.COLLECTION
            ):

                if not any(
                    (
                        self.asset_type,
                        self.role,
                        self.criticality,
                    )
                ):

                    raise ValueError(
                        "STATUS COLLECTION investigation "
                        "requires at least one canonical "
                        "asset selector."
                    )

            contracts = {
                "asset_type":
                    AssetType,

                "role":
                    AssetRole,

                "criticality":
                    Criticality,

                "status_filter":
                    AssetStatus,
            }

            for (
                field_name,
                enum_type,
            ) in contracts.items():

                value = getattr(
                    self,
                    field_name,
                )

                if (
                    value is not None
                    and value
                    not in enum_type.__members__
                ):

                    raise ValueError(
                        f"Unsupported {field_name}: "
                        f"{value}"
                    )

        else:

            # Status-specific selectors have no authority outside
            # STATUS investigations. Structured output noise is
            # canonicalized away rather than changing semantics.
            self.asset_type = None
            self.role = None
            self.criticality = None
            self.status_filter = None

        if (
            self.domain
            != EvidenceDomain.UNKNOWN
            and self.scope_mode
            == InvestigationScopeMode.TARGET
            and not self.target_query
        ):

            raise ValueError(
                "TARGET investigation requires "
                "target_query."
            )

        return self


class ScopeBuildResult(BaseModel):

    status: str

    scope: InvestigationScope | None = None

    reason: str | None = None


def build_investigation_scope(
    plan: InvestigationPlan,
    *,
    target_asset_ids: set[str] | None = None,
) -> ScopeBuildResult:
    """
    Build the deterministic evidence scope after ATLAS has
    resolved the plan's human-readable target.

    target_asset_ids may contain one asset or all members of
    a semantic group.
    """

    targets = {
        str(asset_id).strip()
        for asset_id in (
            target_asset_ids
            or set()
        )
        if str(asset_id).strip()
    }

    # GLOBAL and COLLECTION investigations do not resolve one
    # concrete entity target.
    if (
        plan.scope_mode
        in {
            InvestigationScopeMode.GLOBAL,
            InvestigationScopeMode.COLLECTION,
        }
    ):

        targets = set()

    elif (
        plan.target_query
        and not targets
    ):

        return ScopeBuildResult(
            status="UNRESOLVED_TARGET",
            reason=(
                "The investigation target was not "
                "resolved to any ATLAS asset."
            ),
        )

    scope = InvestigationScope(
        domain=plan.domain,
        scope_mode=plan.scope_mode,
        collection_query=plan.collection_query,
        target_asset_ids=targets,
        relationship=plan.relationship,
        direction=(
            plan.direction.value
            if plan.direction
            is not None
            else None
        ),
        asset_type=plan.asset_type,
        role=plan.role,
        criticality=plan.criticality,
        status_filter=plan.status_filter,
    )

    return ScopeBuildResult(
        status="SUCCESS",
        scope=scope,
    )
