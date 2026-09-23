from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import (
    BaseModel,
    Field,
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

from atlas.services.ai.investigator.contracts import (
    AttentionFact,
    RelationFact,
    StatusFact,
    StatusQueryFact,
)
from atlas.services.ai.investigator.evidence import (
    EvidenceLedger,
)


class EvidenceDomain(StrEnum):
    """
    Semantic evidence family required by an investigation.

    These are capability domains, not natural-language question rules.
    """

    RELATION = "RELATION"

    ATTENTION = "ATTENTION"

    STATUS = "STATUS"

    OBSERVATION = "OBSERVATION"

    IMPACT = "IMPACT"

    HEALTH = "HEALTH"

    UNKNOWN = "UNKNOWN"


class InvestigationScopeMode(StrEnum):
    """
    Semantic breadth of an investigation.

    TARGET:
        one concrete infrastructure entity.

    COLLECTION:
        a semantic population or category of entities.

    GLOBAL:
        the infrastructure as a whole.
    """

    TARGET = "TARGET"

    COLLECTION = "COLLECTION"

    GLOBAL = "GLOBAL"


class InvestigationScope(BaseModel):
    """
    Deterministic admissibility boundary for verified evidence.

    A fact can be true in ATLAS while still being outside the
    scope of the current investigation.
    """

    domain: EvidenceDomain

    scope_mode: InvestigationScopeMode

    collection_query: str | None = None

    target_asset_ids: set[str] = Field(
        default_factory=set
    )

    relationship: str | None = None

    direction: Literal[
        "UPSTREAM",
        "DOWNSTREAM",
    ] | None = None

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
        Keep Python callers using global_scope compatible while
        removing global_scope from the canonical input schema.
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
        "target_asset_ids"
    )
    @classmethod
    def normalize_targets(
        cls,
        value,
    ):

        return {
            str(item).strip()
            for item in value
            if str(item).strip()
        }


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
        "direction"
    )
    @classmethod
    def normalize_direction(
        cls,
        value,
    ):

        if value is None:
            return None

        normalized = str(
            value
        ).strip().upper()

        if normalized not in {
            "UPSTREAM",
            "DOWNSTREAM",
        }:

            raise ValueError(
                "direction must be "
                "UPSTREAM or DOWNSTREAM"
            )

        return normalized


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
    def canonicalize_scope(
        self,
    ):

        if (
            self.scope_mode
            == InvestigationScopeMode.GLOBAL
        ):

            self.collection_query = None
            self.target_asset_ids = set()

        elif (
            self.scope_mode
            == InvestigationScopeMode.COLLECTION
        ):

            if not self.collection_query:

                raise ValueError(
                    "COLLECTION scope requires "
                    "collection_query."
                )

            self.target_asset_ids = set()

        else:

            self.collection_query = None

        # ----------------------------------------------------------
        # STATUS selector semantics.
        # ----------------------------------------------------------

        if (
            self.domain
            == EvidenceDomain.STATUS
        ):

            if (
                self.scope_mode
                == InvestigationScopeMode.TARGET
            ):

                self.asset_type = None
                self.role = None
                self.criticality = None
                self.status_filter = None

            elif (
                self.scope_mode
                == InvestigationScopeMode.GLOBAL
            ):

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
                        "STATUS COLLECTION scope "
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

            self.asset_type = None
            self.role = None
            self.criticality = None
            self.status_filter = None

        return self


class ScopeValidation(BaseModel):

    accepted_fact_ids: list[str] = Field(
        default_factory=list
    )

    rejected_fact_ids: list[str] = Field(
        default_factory=list
    )

    reasons: dict[str, str] = Field(
        default_factory=dict
    )

    @property
    def valid(
        self,
    ) -> bool:

        return not self.rejected_fact_ids


def _relation_in_scope(
    scope: InvestigationScope,
    fact: RelationFact,
) -> tuple[
    bool,
    str,
]:

    if (
        scope.domain
        != EvidenceDomain.RELATION
    ):

        return (
            False,
            "EVIDENCE_DOMAIN_MISMATCH",
        )

    if (
        scope.relationship
        and fact.predicate
        != scope.relationship
    ):

        return (
            False,
            "RELATIONSHIP_MISMATCH",
        )

    if scope.target_asset_ids:

        # ----------------------------------------------------------
        # Canonical relationship:
        #
        #     subject -> predicate -> object
        #
        # DOWNSTREAM means:
        #     what does the scoped target depend on?
        #     therefore target must be the subject.
        #
        # UPSTREAM means:
        #     what depends on the scoped target?
        #     therefore target must be the object.
        # ----------------------------------------------------------

        if (
            scope.direction
            == "DOWNSTREAM"
        ):

            if (
                fact.subject_id
                not in scope.target_asset_ids
            ):

                return (
                    False,
                    "TARGET_DIRECTION_MISMATCH",
                )

        elif (
            scope.direction
            == "UPSTREAM"
        ):

            if (
                fact.object_id
                not in scope.target_asset_ids
            ):

                return (
                    False,
                    "TARGET_DIRECTION_MISMATCH",
                )

        else:

            related_assets = {
                fact.subject_id,
                fact.object_id,
            }

            if not (
                related_assets
                & scope.target_asset_ids
            ):

                return (
                    False,
                    "TARGET_MISMATCH",
                )

    return (
        True,
        "SUPPORTED",
    )


def _attention_in_scope(
    scope: InvestigationScope,
    fact: AttentionFact,
) -> tuple[
    bool,
    str,
]:

    # --------------------------------------------------------------
    # GLOBAL OPERATIONAL ATTENTION
    # --------------------------------------------------------------

    if (
        scope.domain
        == EvidenceDomain.ATTENTION
    ):

        if scope.global_scope:

            return (
                True,
                "SUPPORTED",
            )

        if (
            scope.target_asset_ids
            and fact.asset_id
            in scope.target_asset_ids
        ):

            return (
                True,
                "SUPPORTED",
            )

        return (
            False,
            "TARGET_MISMATCH",
        )

    # --------------------------------------------------------------
    # ENTITY HEALTH
    #
    # For now only direct attention attached to a scoped asset
    # qualifies as health evidence.
    #
    # Later topology/impact expansion can enrich target_asset_ids
    # without changing this validator.
    # --------------------------------------------------------------

    if (
        scope.domain
        == EvidenceDomain.HEALTH
    ):

        if (
            fact.asset_id
            and fact.asset_id
            in scope.target_asset_ids
        ):

            return (
                True,
                "SUPPORTED",
            )

        return (
            False,
            "TARGET_MISMATCH",
        )

    return (
        False,
        "EVIDENCE_DOMAIN_MISMATCH",
    )


def _status_query_in_scope(
    scope: InvestigationScope,
    fact: StatusQueryFact,
) -> tuple[
    bool,
    str,
]:

    if (
        scope.domain
        != EvidenceDomain.STATUS
    ):

        return (
            False,
            "EVIDENCE_DOMAIN_MISMATCH",
        )

    if not fact.complete:

        return (
            False,
            "INCOMPLETE_STATUS_QUERY",
        )

    if (
        fact.status_filter
        != scope.status_filter
    ):

        return (
            False,
            "STATUS_FILTER_MISMATCH",
        )

    selector_pairs = (
        (
            fact.asset_type,
            scope.asset_type,
        ),
        (
            fact.role,
            scope.role,
        ),
        (
            fact.criticality,
            scope.criticality,
        ),
    )

    if any(
        fact_value
        != scope_value
        for (
            fact_value,
            scope_value,
        )
        in selector_pairs
    ):

        return (
            False,
            "SELECTOR_MISMATCH",
        )

    return (
        True,
        "SUPPORTED",
    )


def _status_in_scope(
    scope: InvestigationScope,
    fact: StatusFact,
) -> tuple[
    bool,
    str,
]:

    if (
        scope.domain
        != EvidenceDomain.STATUS
    ):

        return (
            False,
            "EVIDENCE_DOMAIN_MISMATCH",
        )

    if (
        scope.scope_mode
        == InvestigationScopeMode.TARGET
        and (
            not scope.target_asset_ids
            or fact.asset_id
            not in scope.target_asset_ids
        )
    ):

        return (
            False,
            "TARGET_MISMATCH",
        )

    if (
        scope.asset_type
        and fact.asset_type
        != scope.asset_type
    ):

        return (
            False,
            "SELECTOR_MISMATCH",
        )

    if (
        scope.criticality
        and fact.criticality
        != scope.criticality
    ):

        return (
            False,
            "SELECTOR_MISMATCH",
        )

    if (
        scope.role
        and scope.role
        not in {
            str(
                role
            ).strip().upper()
            for role in fact.roles
        }
    ):

        return (
            False,
            "SELECTOR_MISMATCH",
        )

    if (
        scope.status_filter
        and fact.status
        != scope.status_filter
    ):

        return (
            False,
            "STATUS_FILTER_MISMATCH",
        )

    return (
        True,
        "SUPPORTED",
    )


def fact_in_scope(
    scope: InvestigationScope,
    fact,
) -> tuple[
    bool,
    str,
]:

    if isinstance(
        fact,
        RelationFact,
    ):

        return _relation_in_scope(
            scope,
            fact,
        )

    if isinstance(
        fact,
        AttentionFact,
    ):

        return _attention_in_scope(
            scope,
            fact,
        )

    if isinstance(
        fact,
        StatusQueryFact,
    ):

        return _status_query_in_scope(
            scope,
            fact,
        )

    if isinstance(
        fact,
        StatusFact,
    ):

        return _status_in_scope(
            scope,
            fact,
        )

    return (
        False,
        "UNSUPPORTED_FACT_KIND",
    )


def validate_fact_selection(
    scope: InvestigationScope,
    ledger: EvidenceLedger,
    fact_ids: list[str],
) -> ScopeValidation:

    result = ScopeValidation()

    seen = set()

    selected_fact_ids = {
        str(
            fact_id
        )
        for fact_id in fact_ids
    }

    for fact_id in fact_ids:

        if fact_id in seen:
            continue

        seen.add(
            fact_id
        )

        fact = ledger.facts.get(
            fact_id
        )

        if fact is None:

            result.rejected_fact_ids.append(
                fact_id
            )

            result.reasons[
                fact_id
            ] = "UNKNOWN_FACT"

            continue

        # ----------------------------------------------------------
        # A StatusFact is not independently authoritative for this
        # investigation. It must remain linked to the verified
        # StatusQueryFact that produced it, and that query fact must
        # itself be selected and in scope.
        # ----------------------------------------------------------

        if isinstance(
            fact,
            StatusFact,
        ):

            query_fact = ledger.facts.get(
                fact.query_fact_id
            )

            if not isinstance(
                query_fact,
                StatusQueryFact,
            ):

                result.rejected_fact_ids.append(
                    fact_id
                )

                result.reasons[
                    fact_id
                ] = "MISSING_STATUS_QUERY"

                continue

            if (
                fact.query_fact_id
                not in selected_fact_ids
            ):

                result.rejected_fact_ids.append(
                    fact_id
                )

                result.reasons[
                    fact_id
                ] = "STATUS_QUERY_NOT_SELECTED"

                continue

            (
                query_allowed,
                _query_reason,
            ) = _status_query_in_scope(
                scope,
                query_fact,
            )

            if not query_allowed:

                result.rejected_fact_ids.append(
                    fact_id
                )

                result.reasons[
                    fact_id
                ] = (
                    "STATUS_QUERY_SCOPE_MISMATCH"
                )

                continue

        allowed, reason = fact_in_scope(
            scope,
            fact,
        )

        if allowed:

            result.accepted_fact_ids.append(
                fact_id
            )

        else:

            result.rejected_fact_ids.append(
                fact_id
            )

            result.reasons[
                fact_id
            ] = reason

    return result
