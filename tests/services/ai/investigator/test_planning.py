import pytest

from pydantic import ValidationError

from atlas.services.ai.investigator import (
    EvidenceDomain,
    EvidenceLedger,
    InvestigationDirection,
    InvestigationPlan,
    InvestigationScope,
    InvestigationScopeMode,
    RelationAnchor,
    StatusFact,
    StatusQueryFact,
    build_investigation_scope,
    fact_in_scope,
    validate_fact_selection,
)


def test_relation_plan_is_structured():

    plan = InvestigationPlan(
        domain=EvidenceDomain.RELATION,
        target_query="  nebula  ",
        relationship="depends_on",
        relation_anchor=(
            RelationAnchor.SUBJECT
        ),
    )

    assert (
        plan.target_query
        == "nebula"
    )

    assert (
        plan.relationship
        == "DEPENDS_ON"
    )

    assert (
        plan.relation_anchor
        == RelationAnchor.SUBJECT
    )

    assert (
        plan.direction
        == InvestigationDirection.DOWNSTREAM
    )


def test_relation_object_anchor_derives_upstream():

    plan = InvestigationPlan(
        domain=EvidenceDomain.RELATION,
        target_query="database-alpha",
        relationship="DEPENDS_ON",
        relation_anchor=(
            RelationAnchor.OBJECT
        ),
    )

    assert (
        plan.direction
        == InvestigationDirection.UPSTREAM
    )


def test_relation_requires_target():

    with pytest.raises(
        ValidationError
    ):

        InvestigationPlan(
            domain=EvidenceDomain.RELATION,
            relationship="DEPENDS_ON",
            relation_anchor=(
                RelationAnchor.SUBJECT
            ),
        )


def test_relation_requires_relationship():

    with pytest.raises(
        ValidationError
    ):

        InvestigationPlan(
            domain=EvidenceDomain.RELATION,
            target_query="nebula",
            relation_anchor=(
                RelationAnchor.SUBJECT
            ),
        )


def test_relation_requires_anchor():

    with pytest.raises(
        ValidationError
    ):

        InvestigationPlan(
            domain=EvidenceDomain.RELATION,
            target_query="nebula",
            relationship="DEPENDS_ON",
        )


def test_relation_rejects_external_direction():

    with pytest.raises(
        ValidationError
    ):

        InvestigationPlan(
            domain=EvidenceDomain.RELATION,
            target_query="nebula",
            relationship="DEPENDS_ON",
            relation_anchor=(
                RelationAnchor.SUBJECT
            ),
            direction="UPSTREAM",
        )


def test_non_relation_canonicalizes_relation_fields():

    plan = InvestigationPlan(
        domain=EvidenceDomain.HEALTH,
        target_query="nebula",
        relationship="DEPENDS_ON",
        relation_anchor=(
            RelationAnchor.SUBJECT
        ),
    )

    assert (
        plan.relationship
        is None
    )

    assert (
        plan.relation_anchor
        is None
    )

    assert (
        plan.direction
        is None
    )


def test_global_attention_plan():

    plan = InvestigationPlan(
        domain=EvidenceDomain.ATTENTION,
        global_scope=True,
    )

    assert (
        plan.global_scope
        is True
    )

    assert plan.target_query is None

    assert plan.direction is None


def test_global_status_plan():

    plan = InvestigationPlan(
        domain=EvidenceDomain.STATUS,
        global_scope=True,
    )

    assert (
        plan.domain
        == EvidenceDomain.STATUS
    )


def test_targeted_observation_plan():

    plan = InvestigationPlan(
        domain=EvidenceDomain.OBSERVATION,
        target_query="  storage-alpha  ",
        observation="  temperature  ",
    )

    assert (
        plan.target_query
        == "storage-alpha"
    )

    assert (
        plan.observation
        == "temperature"
    )

    assert plan.global_scope is False


def test_observation_requires_observation_intent():

    with pytest.raises(
        ValidationError
    ):

        InvestigationPlan(
            domain=EvidenceDomain.OBSERVATION,
            target_query="storage-alpha",
        )


def test_non_observation_canonicalizes_observation_noise():

    plan = InvestigationPlan(
        domain=EvidenceDomain.HEALTH,
        target_query="nebula",
        observation="temperature",
    )

    assert plan.observation is None


def test_builds_relation_scope_from_subject_anchor():

    plan = InvestigationPlan(
        domain=EvidenceDomain.RELATION,
        target_query="nebula",
        relationship="DEPENDS_ON",
        relation_anchor=(
            RelationAnchor.SUBJECT
        ),
    )

    result = build_investigation_scope(
        plan,
        target_asset_ids={
            "app-nebula",
        },
    )

    assert result.status == "SUCCESS"

    assert result.scope is not None

    assert (
        result.scope.domain
        == EvidenceDomain.RELATION
    )

    assert (
        result.scope.relationship
        == "DEPENDS_ON"
    )

    assert (
        result.scope.direction
        == "DOWNSTREAM"
    )

    assert (
        result.scope.target_asset_ids
        == {
            "app-nebula",
        }
    )


def test_builds_relation_scope_from_object_anchor():

    plan = InvestigationPlan(
        domain=EvidenceDomain.RELATION,
        target_query="database-alpha",
        relationship="DEPENDS_ON",
        relation_anchor=(
            RelationAnchor.OBJECT
        ),
    )

    result = build_investigation_scope(
        plan,
        target_asset_ids={
            "database-alpha",
        },
    )

    assert result.status == "SUCCESS"

    assert result.scope is not None

    assert (
        result.scope.direction
        == "UPSTREAM"
    )


def test_group_members_become_scope_targets():

    plan = InvestigationPlan(
        domain=EvidenceDomain.HEALTH,
        target_query="nebula",
    )

    result = build_investigation_scope(
        plan,
        target_asset_ids={
            "nebula-api",
            "nebula-db",
            "nebula-worker",
        },
    )

    assert result.status == "SUCCESS"

    assert (
        result.scope.target_asset_ids
        == {
            "nebula-api",
            "nebula-db",
            "nebula-worker",
        }
    )


def test_unresolved_target_fails_closed():

    plan = InvestigationPlan(
        domain=EvidenceDomain.HEALTH,
        target_query="missing-stack",
    )

    result = build_investigation_scope(
        plan,
        target_asset_ids=set(),
    )

    assert (
        result.status
        == "UNRESOLVED_TARGET"
    )

    assert result.scope is None


def test_global_scope_needs_no_resolved_target():

    plan = InvestigationPlan(
        domain=EvidenceDomain.ATTENTION,
        global_scope=True,
    )

    result = build_investigation_scope(
        plan
    )

    assert result.status == "SUCCESS"

    assert result.scope is not None

    assert (
        result.scope.global_scope
        is True
    )


def test_global_attention_discards_incidental_target_query():

    plan = InvestigationPlan(
        domain=EvidenceDomain.ATTENTION,
        target_query="infrastructure",
        global_scope=True,
    )

    assert plan.global_scope is True

    assert plan.target_query is None

    result = build_investigation_scope(
        plan
    )

    assert result.status == "SUCCESS"

    assert result.scope is not None

    assert result.scope.global_scope is True

    assert (
        result.scope.target_asset_ids
        == set()
    )


def test_global_status_discards_category_as_target():

    plan = InvestigationPlan(
        domain=EvidenceDomain.STATUS,
        target_query="applications",
        global_scope=True,
    )

    assert plan.target_query is None

    result = build_investigation_scope(
        plan
    )

    assert result.status == "SUCCESS"

    assert result.scope is not None


def test_global_status_canonicalizes_relation_noise():

    plan = InvestigationPlan(
        domain=EvidenceDomain.STATUS,
        target_query="applications",
        relationship="DEPENDS_ON",
        relation_anchor=(
            RelationAnchor.OBJECT
        ),
        global_scope=True,
    )

    assert (
        plan.domain
        == EvidenceDomain.STATUS
    )

    assert plan.global_scope is True

    assert plan.target_query is None

    assert plan.relationship is None

    assert plan.relation_anchor is None

    assert plan.direction is None

    result = build_investigation_scope(
        plan
    )

    assert result.status == "SUCCESS"

    assert result.scope is not None

    assert result.scope.global_scope is True


def test_collection_plan_is_not_global_or_targeted():

    from atlas.services.ai.investigator import (
        InvestigationScopeMode,
    )

    plan = InvestigationPlan(
        domain=EvidenceDomain.STATUS,
        scope_mode=(
            InvestigationScopeMode
            .COLLECTION
        ),
        collection_query="  applications  ",
        asset_type="APPLICATION",
    )

    assert (
        plan.scope_mode
        == InvestigationScopeMode.COLLECTION
    )

    assert (
        plan.collection_query
        == "applications"
    )

    assert plan.target_query is None

    assert plan.global_scope is False


def test_collection_scope_needs_no_entity_resolution():

    from atlas.services.ai.investigator import (
        InvestigationScopeMode,
    )

    plan = InvestigationPlan(
        domain=EvidenceDomain.STATUS,
        scope_mode=(
            InvestigationScopeMode
            .COLLECTION
        ),
        collection_query="applications",
        asset_type="APPLICATION",
    )

    result = build_investigation_scope(
        plan
    )

    assert result.status == "SUCCESS"

    assert result.scope is not None

    assert (
        result.scope.scope_mode
        == InvestigationScopeMode.COLLECTION
    )

    assert (
        result.scope.collection_query
        == "applications"
    )

    assert (
        result.scope.target_asset_ids
        == set()
    )

    assert result.scope.global_scope is False


def test_global_scope_is_derived_from_scope_mode():

    from atlas.services.ai.investigator import (
        InvestigationScopeMode,
    )

    plan = InvestigationPlan(
        domain=EvidenceDomain.ATTENTION,
        scope_mode=(
            InvestigationScopeMode
            .GLOBAL
        ),
    )

    assert plan.global_scope is True

    assert plan.target_query is None

    assert plan.collection_query is None


def test_planner_schema_uses_scope_mode_not_global_scope():

    schema = (
        InvestigationPlan
        .model_json_schema(
            mode="validation"
        )
    )

    properties = schema.get(
        "properties",
        {},
    )

    required = set(
        schema.get(
            "required",
            [],
        )
    )

    assert "scope_mode" in properties

    assert "scope_mode" in required

    assert "collection_query" in properties

    assert "global_scope" not in properties

    assert "direction" not in properties



def test_status_collection_plan_uses_canonical_selectors():

    plan = InvestigationPlan(
        domain=EvidenceDomain.STATUS,
        scope_mode=(
            InvestigationScopeMode
            .COLLECTION
        ),
        collection_query="applications",
        asset_type=" application ",
        status_filter=" offline ",
    )

    assert (
        plan.asset_type
        == "APPLICATION"
    )

    assert (
        plan.status_filter
        == "OFFLINE"
    )

    assert plan.role is None
    assert plan.criticality is None


def test_status_collection_requires_canonical_selector():

    with pytest.raises(
        ValidationError
    ):

        InvestigationPlan(
            domain=EvidenceDomain.STATUS,
            scope_mode=(
                InvestigationScopeMode
                .COLLECTION
            ),
            collection_query="applications",
            status_filter="OFFLINE",
        )


def test_status_plan_rejects_unknown_canonical_selector():

    with pytest.raises(
        ValidationError
    ):

        InvestigationPlan(
            domain=EvidenceDomain.STATUS,
            scope_mode=(
                InvestigationScopeMode
                .COLLECTION
            ),
            collection_query="applications",
            asset_type="MAGICAL_APP",
            status_filter="OFFLINE",
        )


def test_status_plan_rejects_unknown_status_filter():

    with pytest.raises(
        ValidationError
    ):

        InvestigationPlan(
            domain=EvidenceDomain.STATUS,
            scope_mode=(
                InvestigationScopeMode
                .COLLECTION
            ),
            collection_query="applications",
            asset_type="APPLICATION",
            status_filter="BROKEN",
        )


def test_target_status_plan_clears_expected_state_filters():

    plan = InvestigationPlan(
        domain=EvidenceDomain.STATUS,
        scope_mode=(
            InvestigationScopeMode
            .TARGET
        ),
        target_query="app-alpha",
        asset_type="APPLICATION",
        status_filter="OFFLINE",
    )

    assert plan.asset_type is None
    assert plan.role is None
    assert plan.criticality is None
    assert plan.status_filter is None


def test_global_status_plan_keeps_only_status_condition():

    plan = InvestigationPlan(
        domain=EvidenceDomain.STATUS,
        scope_mode=(
            InvestigationScopeMode
            .GLOBAL
        ),
        asset_type="APPLICATION",
        role="MONITORING_NODE",
        criticality="CRITICAL",
        status_filter="DEGRADED",
    )

    assert plan.asset_type is None
    assert plan.role is None
    assert plan.criticality is None

    assert (
        plan.status_filter
        == "DEGRADED"
    )


def test_non_status_plan_canonicalizes_status_selector_noise():

    plan = InvestigationPlan(
        domain=EvidenceDomain.HEALTH,
        scope_mode=(
            InvestigationScopeMode
            .TARGET
        ),
        target_query="app-alpha",
        asset_type="MAGICAL_APP",
        status_filter="BROKEN",
    )

    assert plan.asset_type is None
    assert plan.role is None
    assert plan.criticality is None
    assert plan.status_filter is None


def test_build_scope_carries_status_selectors():

    plan = InvestigationPlan(
        domain=EvidenceDomain.STATUS,
        scope_mode=(
            InvestigationScopeMode
            .COLLECTION
        ),
        collection_query="applications",
        asset_type="APPLICATION",
        criticality="HIGH",
        status_filter="OFFLINE",
    )

    built = build_investigation_scope(
        plan
    )

    assert (
        built.status
        == "SUCCESS"
    )

    assert built.scope is not None

    assert (
        built.scope.asset_type
        == "APPLICATION"
    )

    assert (
        built.scope.criticality
        == "HIGH"
    )

    assert (
        built.scope.status_filter
        == "OFFLINE"
    )

    assert (
        built.scope.target_asset_ids
        == set()
    )


def _status_collection_scope():

    return InvestigationScope(
        domain=EvidenceDomain.STATUS,
        scope_mode=(
            InvestigationScopeMode
            .COLLECTION
        ),
        collection_query="applications",
        asset_type="APPLICATION",
        status_filter="OFFLINE",
    )


def test_complete_zero_status_query_is_in_scope():

    scope = _status_collection_scope()

    fact = StatusQueryFact(
        id="FACT-001",
        complete=True,
        count=0,
        status_filter="OFFLINE",
        asset_type="APPLICATION",
        criticality=None,
        role=None,
        source_tool=(
            "atlas_query_asset_status"
        ),
    )

    allowed, reason = fact_in_scope(
        scope,
        fact,
    )

    assert allowed is True

    assert (
        reason
        == "SUPPORTED"
    )


def test_status_query_rejects_status_filter_mismatch():

    scope = _status_collection_scope()

    fact = StatusQueryFact(
        id="FACT-001",
        complete=True,
        count=0,
        status_filter="ONLINE",
        asset_type="APPLICATION",
        criticality=None,
        role=None,
        source_tool=(
            "atlas_query_asset_status"
        ),
    )

    allowed, reason = fact_in_scope(
        scope,
        fact,
    )

    assert allowed is False

    assert (
        reason
        == "STATUS_FILTER_MISMATCH"
    )


def test_status_query_rejects_selector_mismatch():

    scope = _status_collection_scope()

    fact = StatusQueryFact(
        id="FACT-001",
        complete=True,
        count=0,
        status_filter="OFFLINE",
        asset_type="SERVER",
        criticality=None,
        role=None,
        source_tool=(
            "atlas_query_asset_status"
        ),
    )

    allowed, reason = fact_in_scope(
        scope,
        fact,
    )

    assert allowed is False

    assert (
        reason
        == "SELECTOR_MISMATCH"
    )


def test_status_query_rejects_incomplete_inventory_evidence():

    scope = _status_collection_scope()

    fact = StatusQueryFact(
        id="FACT-001",
        complete=False,
        count=0,
        status_filter="OFFLINE",
        asset_type="APPLICATION",
        criticality=None,
        role=None,
        source_tool=(
            "atlas_query_asset_status"
        ),
    )

    allowed, reason = fact_in_scope(
        scope,
        fact,
    )

    assert allowed is False

    assert (
        reason
        == "INCOMPLETE_STATUS_QUERY"
    )


def test_target_status_fact_requires_target_asset():

    scope = InvestigationScope(
        domain=EvidenceDomain.STATUS,
        scope_mode=(
            InvestigationScopeMode
            .TARGET
        ),
        target_asset_ids={
            "application-alpha",
        },
    )

    fact = StatusFact(
        id="FACT-002",
        query_fact_id="FACT-001",
        asset_id="application-beta",
        asset_name="app-beta",
        asset_type="APPLICATION",
        status="OFFLINE",
        source_tool=(
            "atlas_query_asset_status"
        ),
    )

    allowed, reason = fact_in_scope(
        scope,
        fact,
    )

    assert allowed is False

    assert (
        reason
        == "TARGET_MISMATCH"
    )


def test_status_fact_requires_selected_status_query_fact():

    scope = _status_collection_scope()

    ledger = EvidenceLedger()

    query = StatusQueryFact(
        id="FACT-001",
        complete=True,
        count=1,
        status_filter="OFFLINE",
        asset_type="APPLICATION",
        criticality=None,
        role=None,
        source_tool=(
            "atlas_query_asset_status"
        ),
    )

    status = StatusFact(
        id="FACT-002",
        query_fact_id="FACT-001",
        asset_id="application-alpha",
        asset_name="app-alpha",
        asset_type="APPLICATION",
        status="OFFLINE",
        source_tool=(
            "atlas_query_asset_status"
        ),
    )

    ledger.facts[
        query.id
    ] = query

    ledger.facts[
        status.id
    ] = status

    validation = validate_fact_selection(
        scope,
        ledger,
        [
            status.id,
        ],
    )

    assert (
        validation.valid
        is False
    )

    assert (
        validation.reasons[
            status.id
        ]
        == "STATUS_QUERY_NOT_SELECTED"
    )


def test_status_fact_and_query_chain_are_accepted():

    scope = _status_collection_scope()

    ledger = EvidenceLedger()

    query = StatusQueryFact(
        id="FACT-001",
        complete=True,
        count=1,
        status_filter="OFFLINE",
        asset_type="APPLICATION",
        criticality=None,
        role=None,
        source_tool=(
            "atlas_query_asset_status"
        ),
    )

    status = StatusFact(
        id="FACT-002",
        query_fact_id="FACT-001",
        asset_id="application-alpha",
        asset_name="app-alpha",
        asset_type="APPLICATION",
        status="OFFLINE",
        source_tool=(
            "atlas_query_asset_status"
        ),
    )

    ledger.facts[
        query.id
    ] = query

    ledger.facts[
        status.id
    ] = status

    validation = validate_fact_selection(
        scope,
        ledger,
        [
            query.id,
            status.id,
        ],
    )

    assert validation.valid is True

    assert (
        validation.accepted_fact_ids
        == [
            "FACT-001",
            "FACT-002",
        ]
    )
