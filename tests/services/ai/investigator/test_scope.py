from atlas.services.ai.investigator import (
    AttentionFact,
    EvidenceDomain,
    EvidenceLedger,
    InvestigationScope,
    RelationFact,
    validate_fact_selection,
)


def relation_ledger():

    ledger = EvidenceLedger()

    ledger.facts[
        "FACT-001"
    ] = RelationFact(
        id="FACT-001",
        subject_id="app-alpha",
        subject_name="app-alpha",
        predicate="DEPENDS_ON",
        object_id="db-alpha",
        object_name="db-alpha",
        confidence=0.99,
        source_tool=(
            "atlas_query_entity_relations"
        ),
    )

    return ledger


def attention_ledger(
    *,
    asset_id="asset-alpha",
):

    ledger = EvidenceLedger()

    ledger.facts[
        "FACT-001"
    ] = AttentionFact(
        id="FACT-001",
        signal_kind="INCIDENT",
        signal_id="INC-TEST",
        asset_id=asset_id,
        severity="HIGH",
        status="OPEN",
        title="synthetic_degradation",
        source_tool=(
            "atlas_attention_summary"
        ),
    )

    return ledger


def test_relation_is_accepted_for_matching_target():

    ledger = relation_ledger()

    scope = InvestigationScope(
        domain=EvidenceDomain.RELATION,
        target_asset_ids={
            "app-alpha",
        },
        relationship="DEPENDS_ON",
    )

    result = validate_fact_selection(
        scope,
        ledger,
        [
            "FACT-001",
        ],
    )

    assert result.valid is True

    assert (
        result.accepted_fact_ids
        == [
            "FACT-001",
        ]
    )


def test_relation_matches_when_target_is_object():

    ledger = relation_ledger()

    scope = InvestigationScope(
        domain=EvidenceDomain.RELATION,
        target_asset_ids={
            "db-alpha",
        },
        relationship="DEPENDS_ON",
    )

    result = validate_fact_selection(
        scope,
        ledger,
        [
            "FACT-001",
        ],
    )

    assert result.valid is True


def test_unrelated_relation_is_rejected():

    ledger = relation_ledger()

    scope = InvestigationScope(
        domain=EvidenceDomain.RELATION,
        target_asset_ids={
            "other-asset",
        },
        relationship="DEPENDS_ON",
    )

    result = validate_fact_selection(
        scope,
        ledger,
        [
            "FACT-001",
        ],
    )

    assert result.valid is False

    assert (
        result.reasons[
            "FACT-001"
        ]
        == "TARGET_MISMATCH"
    )


def test_wrong_relationship_is_rejected():

    ledger = relation_ledger()

    scope = InvestigationScope(
        domain=EvidenceDomain.RELATION,
        target_asset_ids={
            "app-alpha",
        },
        relationship="MONITORS",
    )

    result = validate_fact_selection(
        scope,
        ledger,
        [
            "FACT-001",
        ],
    )

    assert result.valid is False

    assert (
        result.reasons[
            "FACT-001"
        ]
        == "RELATIONSHIP_MISMATCH"
    )


def test_global_attention_accepts_operational_signal():

    ledger = attention_ledger()

    scope = InvestigationScope(
        domain=EvidenceDomain.ATTENTION,
        global_scope=True,
    )

    result = validate_fact_selection(
        scope,
        ledger,
        [
            "FACT-001",
        ],
    )

    assert result.valid is True


def test_attention_cannot_answer_status_question():

    ledger = attention_ledger()

    scope = InvestigationScope(
        domain=EvidenceDomain.STATUS,
        global_scope=True,
    )

    result = validate_fact_selection(
        scope,
        ledger,
        [
            "FACT-001",
        ],
    )

    assert result.valid is False

    assert (
        result.reasons[
            "FACT-001"
        ]
        == "EVIDENCE_DOMAIN_MISMATCH"
    )


def test_attention_cannot_answer_observation_question():

    ledger = attention_ledger()

    scope = InvestigationScope(
        domain=EvidenceDomain.OBSERVATION,
        target_asset_ids={
            "asset-alpha",
        },
    )

    result = validate_fact_selection(
        scope,
        ledger,
        [
            "FACT-001",
        ],
    )

    assert result.valid is False


def test_unrelated_attention_cannot_prove_entity_health():

    ledger = attention_ledger(
        asset_id="infrastructure-beta"
    )

    scope = InvestigationScope(
        domain=EvidenceDomain.HEALTH,
        target_asset_ids={
            "application-alpha",
        },
    )

    result = validate_fact_selection(
        scope,
        ledger,
        [
            "FACT-001",
        ],
    )

    assert result.valid is False

    assert (
        result.reasons[
            "FACT-001"
        ]
        == "TARGET_MISMATCH"
    )


def test_direct_attention_can_support_entity_health():

    ledger = attention_ledger(
        asset_id="application-alpha"
    )

    scope = InvestigationScope(
        domain=EvidenceDomain.HEALTH,
        target_asset_ids={
            "application-alpha",
        },
    )

    result = validate_fact_selection(
        scope,
        ledger,
        [
            "FACT-001",
        ],
    )

    assert result.valid is True


def test_unknown_fact_id_is_rejected():

    ledger = relation_ledger()

    scope = InvestigationScope(
        domain=EvidenceDomain.RELATION,
        global_scope=True,
    )

    result = validate_fact_selection(
        scope,
        ledger,
        [
            "FACT-999",
        ],
    )

    assert result.valid is False

    assert (
        result.reasons[
            "FACT-999"
        ]
        == "UNKNOWN_FACT"
    )


def test_downstream_relation_requires_target_as_subject():

    ledger = relation_ledger()

    scope = InvestigationScope(
        domain=EvidenceDomain.RELATION,
        target_asset_ids={
            "app-alpha",
        },
        relationship="DEPENDS_ON",
        direction="DOWNSTREAM",
    )

    result = validate_fact_selection(
        scope,
        ledger,
        [
            "FACT-001",
        ],
    )

    assert result.valid is True


def test_downstream_rejects_target_on_object_side():

    ledger = relation_ledger()

    scope = InvestigationScope(
        domain=EvidenceDomain.RELATION,
        target_asset_ids={
            "db-alpha",
        },
        relationship="DEPENDS_ON",
        direction="DOWNSTREAM",
    )

    result = validate_fact_selection(
        scope,
        ledger,
        [
            "FACT-001",
        ],
    )

    assert result.valid is False

    assert (
        result.reasons[
            "FACT-001"
        ]
        == "TARGET_DIRECTION_MISMATCH"
    )


def test_upstream_relation_requires_target_as_object():

    ledger = relation_ledger()

    scope = InvestigationScope(
        domain=EvidenceDomain.RELATION,
        target_asset_ids={
            "db-alpha",
        },
        relationship="DEPENDS_ON",
        direction="UPSTREAM",
    )

    result = validate_fact_selection(
        scope,
        ledger,
        [
            "FACT-001",
        ],
    )

    assert result.valid is True


def test_upstream_rejects_target_on_subject_side():

    ledger = relation_ledger()

    scope = InvestigationScope(
        domain=EvidenceDomain.RELATION,
        target_asset_ids={
            "app-alpha",
        },
        relationship="DEPENDS_ON",
        direction="UPSTREAM",
    )

    result = validate_fact_selection(
        scope,
        ledger,
        [
            "FACT-001",
        ],
    )

    assert result.valid is False

    assert (
        result.reasons[
            "FACT-001"
        ]
        == "TARGET_DIRECTION_MISMATCH"
    )
