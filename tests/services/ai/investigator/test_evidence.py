from atlas.services.ai.investigator import (
    AttentionFact,
    EvidenceLedger,
    InvestigationReport,
    RelationFact,
    render_report,
)


def semantic_relation_payload(
    *,
    direction="DOWNSTREAM",
):

    return {
        "status": "SUCCESS",
        "results": [
            {
                "asset_id":
                    "dependency-alpha",

                "name":
                    "dependency-alpha",

                "relationship":
                    "DEPENDS_ON",

                "direction":
                    direction,

                "confidence":
                    0.99,

                "evidence": [
                    "synthetic relationship",
                ],

                "root_member_id":
                    "application-alpha",

                "source_asset_id":
                    "application-alpha",

                "source_name":
                    "application-alpha",

                "target_asset_id":
                    "dependency-alpha",

                "target_name":
                    "dependency-alpha",
            }
        ],
    }


def test_ingests_canonical_relation_fact():

    ledger = EvidenceLedger()

    ids = ledger.ingest(
        "atlas_query_entity_relations",
        semantic_relation_payload(),
    )

    assert ids == [
        "FACT-001"
    ]

    fact = ledger.facts[
        "FACT-001"
    ]

    assert isinstance(
        fact,
        RelationFact,
    )

    assert (
        fact.subject_id
        == "application-alpha"
    )

    assert (
        fact.predicate
        == "DEPENDS_ON"
    )

    assert (
        fact.object_id
        == "dependency-alpha"
    )


def test_relation_fact_is_canonical_even_for_upstream_query():

    ledger = EvidenceLedger()

    ledger.ingest(
        "atlas_query_entity_relations",
        semantic_relation_payload(
            direction="UPSTREAM"
        ),
    )

    fact = ledger.facts[
        "FACT-001"
    ]

    assert (
        fact.subject_id
        == "application-alpha"
    )

    assert (
        fact.object_id
        == "dependency-alpha"
    )


def test_ingests_operational_attention():

    ledger = EvidenceLedger()

    ids = ledger.ingest(
        "atlas_attention_summary",
        {
            "status":
                "SUCCESS",

            "attention":
                {
                    "state":
                        "WARNING",

                    "items":
                        [
                            {
                                "kind":
                                    "INCIDENT",

                                "id":
                                    "INC-TEST",

                                "asset_id":
                                    "asset-alpha",

                                "severity":
                                    "HIGH",

                                "status":
                                    "OPEN",

                                "title":
                                    "service_degradation",

                                "message":
                                    "Synthetic degradation",
                            }
                        ],
                },
        },
    )

    assert ids == [
        "FACT-001"
    ]

    fact = ledger.facts[
        "FACT-001"
    ]

    assert isinstance(
        fact,
        AttentionFact,
    )

    assert (
        fact.signal_id
        == "INC-TEST"
    )

    assert fact.severity == "HIGH"


def test_deduplicates_same_verified_fact():

    ledger = EvidenceLedger()

    first = ledger.ingest(
        "atlas_query_entity_relations",
        semantic_relation_payload(),
    )

    second = ledger.ingest(
        "atlas_query_entity_relations",
        semantic_relation_payload(),
    )

    assert first == [
        "FACT-001"
    ]

    assert second == [
        "FACT-001"
    ]

    assert len(
        ledger.facts
    ) == 1


def test_rejects_unknown_fact_ids():

    ledger = EvidenceLedger()

    ledger.ingest(
        "atlas_query_entity_relations",
        semantic_relation_payload(),
    )

    assert (
        ledger.validate_fact_ids(
            [
                "FACT-001",
                "FACT-999",
            ]
        )
        == [
            "FACT-999"
        ]
    )


def test_renders_verified_dependency():

    ledger = EvidenceLedger()

    ledger.ingest(
        "atlas_query_entity_relations",
        semantic_relation_payload(),
    )

    report = InvestigationReport(
        status="ANSWERED",
        fact_ids=[
            "FACT-001"
        ],
    )

    answer = render_report(
        report,
        ledger,
    )

    assert (
        "application-alpha"
        in answer
    )

    assert (
        "dependency-alpha"
        in answer
    )

    assert (
        "1 dependencia directa registrada"
        in answer
    )


def test_renders_verified_attention():

    ledger = EvidenceLedger()

    ledger.ingest(
        "atlas_attention_summary",
        {
            "status":
                "SUCCESS",

            "attention":
                {
                    "items":
                        [
                            {
                                "kind":
                                    "EVENT",

                                "id":
                                    "EVENT-1",

                                "asset_id":
                                    "asset-alpha",

                                "severity":
                                    "WARNING",

                                "status":
                                    "OPEN",

                                "title":
                                    "Infrastructure Warning",

                                "message":
                                    "Synthetic warning",
                            }
                        ],
                },
        },
    )

    report = InvestigationReport(
        status="ANSWERED",
        fact_ids=[
            "FACT-001"
        ],
    )

    answer = render_report(
        report,
        ledger,
    )

    assert (
        "1 señal verificada"
        in answer
    )

    assert (
        "Infrastructure Warning"
        in answer
    )

    assert "WARNING" in answer


def test_insufficient_evidence_fails_closed():

    ledger = EvidenceLedger()

    report = InvestigationReport(
        status="INSUFFICIENT_EVIDENCE",
    )

    assert render_report(
        report,
        ledger,
    ) == (
        "ATLAS no dispone de evidencia "
        "verificada suficiente para responder."
    )


def test_ingests_complete_zero_status_query_as_verified_fact():

    ledger = EvidenceLedger()

    fact_ids = ledger.ingest(
        "atlas_query_asset_status",
        {
            "data": {
                "status": "SUCCESS",
                "complete": True,
                "count": 0,
                "filters": {
                    "status": "OFFLINE",
                    "asset_type": "APPLICATION",
                    "criticality": None,
                    "role": None,
                },
                "assets": [],
                "evidence": [
                    "complete synthetic inventory query",
                ],
            },
        },
    )

    assert fact_ids == [
        "FACT-001",
    ]

    fact = ledger.facts[
        "FACT-001"
    ]

    assert (
        fact.kind
        == "STATUS_QUERY"
    )

    assert (
        fact.complete
        is True
    )

    assert (
        fact.count
        == 0
    )

    assert (
        fact.status_filter
        == "OFFLINE"
    )

    assert (
        fact.asset_type
        == "APPLICATION"
    )


def test_ingests_status_query_and_asset_status_facts():

    ledger = EvidenceLedger()

    fact_ids = ledger.ingest(
        "atlas_query_asset_status",
        {
            "data": {
                "status": "SUCCESS",
                "complete": True,
                "count": 2,
                "filters": {
                    "status": "OFFLINE",
                    "asset_type": "APPLICATION",
                    "criticality": None,
                    "role": None,
                },
                "assets": [
                    {
                        "id":
                            "application-synthetic-alpha",

                        "name":
                            "app-alpha",

                        "type":
                            "APPLICATION",

                        "status":
                            "OFFLINE",

                        "health":
                            0.0,

                        "criticality":
                            "HIGH",

                        "roles":
                            [
                                "UTILITY_SERVICE",
                            ],

                        "last_seen":
                            "2026-08-29T18:00:00+00:00",
                    },
                    {
                        "id":
                            "application-synthetic-beta",

                        "name":
                            "app-beta",

                        "type":
                            "APPLICATION",

                        "status":
                            "OFFLINE",

                        "health":
                            0.0,

                        "criticality":
                            "MEDIUM",

                        "roles":
                            [],

                        "last_seen":
                            "2026-08-29T18:01:00+00:00",
                    },
                ],
                "evidence": [
                    "complete synthetic inventory query",
                ],
            },
        },
    )

    assert fact_ids == [
        "FACT-001",
        "FACT-002",
        "FACT-003",
    ]

    query = ledger.facts[
        "FACT-001"
    ]

    first = ledger.facts[
        "FACT-002"
    ]

    second = ledger.facts[
        "FACT-003"
    ]

    assert (
        query.kind
        == "STATUS_QUERY"
    )

    assert (
        query.count
        == 2
    )

    assert (
        first.kind
        == "STATUS"
    )

    assert (
        second.kind
        == "STATUS"
    )

    assert (
        first.query_fact_id
        == query.id
    )

    assert (
        first.asset_id
        == "application-synthetic-alpha"
    )

    assert (
        first.status
        == "OFFLINE"
    )

    assert (
        second.asset_id
        == "application-synthetic-beta"
    )


def test_status_ingest_rejects_inconsistent_declared_count():

    ledger = EvidenceLedger()

    fact_ids = ledger.ingest(
        "atlas_query_asset_status",
        {
            "data": {
                "status": "SUCCESS",
                "complete": True,
                "count": 2,
                "filters": {
                    "status": "OFFLINE",
                },
                "assets": [],
            },
        },
    )

    assert fact_ids == []

    assert ledger.facts == {}


def test_status_ingest_rejects_error_result():

    ledger = EvidenceLedger()

    fact_ids = ledger.ingest(
        "atlas_query_asset_status",
        {
            "data": {
                "status": "ERROR",
                "complete": False,
                "count": 0,
                "assets": [],
            },
        },
    )

    assert fact_ids == []

    assert ledger.facts == {}


def test_renders_verified_zero_status_query():

    ledger = EvidenceLedger()

    fact_ids = ledger.ingest(
        "atlas_query_asset_status",
        {
            "data": {
                "status": "SUCCESS",
                "complete": True,
                "count": 0,
                "filters": {
                    "status": "OFFLINE",
                    "asset_type": "APPLICATION",
                    "criticality": None,
                    "role": None,
                },
                "assets": [],
                "evidence": [
                    "complete synthetic inventory query",
                ],
            },
        },
    )

    report = InvestigationReport(
        status="ANSWERED",
        fact_ids=fact_ids,
    )

    answer = render_report(
        report,
        ledger,
    )

    assert (
        "consulta completa"
        in answer
    )

    assert (
        "no encontró"
        in answer
    )

    assert (
        "status=OFFLINE"
        in answer
    )

    assert (
        "asset_type=APPLICATION"
        in answer
    )


def test_renders_verified_status_assets():

    ledger = EvidenceLedger()

    fact_ids = ledger.ingest(
        "atlas_query_asset_status",
        {
            "data": {
                "status": "SUCCESS",
                "complete": True,
                "count": 1,
                "filters": {
                    "status": "OFFLINE",
                    "asset_type": "APPLICATION",
                    "criticality": None,
                    "role": None,
                },
                "assets": [
                    {
                        "id":
                            "application-synthetic-alpha",

                        "name":
                            "app-alpha",

                        "type":
                            "APPLICATION",

                        "status":
                            "OFFLINE",

                        "health":
                            0.0,

                        "criticality":
                            "HIGH",

                        "roles":
                            [],

                        "last_seen":
                            None,
                    },
                ],
                "evidence": [
                    "complete synthetic inventory query",
                ],
            },
        },
    )

    report = InvestigationReport(
        status="ANSWERED",
        fact_ids=fact_ids,
    )

    answer = render_report(
        report,
        ledger,
    )

    assert (
        "1 assets"
        in answer
    )

    assert (
        "`app-alpha`"
        in answer
    )

    assert (
        "OFFLINE"
        in answer
    )

    assert (
        "APPLICATION"
        in answer
    )
