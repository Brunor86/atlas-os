from dataclasses import dataclass

from atlas.services.ai.investigator import (
    AtlasInvestigator,
    EvidenceDomain,
    InvestigationPlan,
    InvestigationScopeMode,
    RelationAnchor,
)


@dataclass
class FakeToolResult:

    success: bool

    data: object = None

    error: str | None = None


class FakePlanner:

    def __init__(
        self,
        plan,
    ):

        self.result = plan
        self.requests = []


    def plan(
        self,
        question,
    ):

        self.requests.append(
            question
        )

        return self.result


class FakeToolBackend:

    def __init__(
        self,
        responses,
    ):

        self.responses = responses
        self.calls = []


    def execute_tool(
        self,
        name,
        **kwargs,
    ):

        self.calls.append(
            (
                name,
                kwargs,
            )
        )

        response = self.responses[
            name
        ]

        if callable(
            response
        ):

            return response(
                **kwargs
            )

        return response


def resolved_asset(
    asset_id="application-alpha",
):

    return FakeToolResult(
        success=True,
        data={
            "status":
                "SUCCESS",

            "kind":
                "ASSET",

            "asset_id":
                asset_id,
        },
    )


def relation_payload(
    *,
    source_asset_id="application-alpha",
    target_asset_id="dependency-alpha",
):

    return {
        "status":
            "SUCCESS",

        "relationship":
            "DEPENDS_ON",

        "direction":
            "DOWNSTREAM",

        "count":
            1,

        "results":
            [
                {
                    "asset_id":
                        target_asset_id,

                    "name":
                        target_asset_id,

                    "relationship":
                        "DEPENDS_ON",

                    "direction":
                        "DOWNSTREAM",

                    "depth":
                        1,

                    "confidence":
                        0.99,

                    "evidence":
                        [
                            "synthetic relationship",
                        ],

                    "root_member_id":
                        source_asset_id,

                    "source_asset_id":
                        source_asset_id,

                    "source_name":
                        source_asset_id,

                    "target_asset_id":
                        target_asset_id,

                    "target_name":
                        target_asset_id,
                }
            ],
    }


def test_relation_plan_executes_derived_mcp_route():

    plan = InvestigationPlan(
        domain=EvidenceDomain.RELATION,
        target_query="photo stack",
        relationship="DEPENDS_ON",
        relation_anchor=(
            RelationAnchor.SUBJECT
        ),
    )

    backend = FakeToolBackend(
        {
            "atlas_resolve_entity":
                resolved_asset(),

            "atlas_query_entity_relations":
                FakeToolResult(
                    success=True,
                    data=relation_payload(),
                ),
        }
    )

    investigator = AtlasInvestigator(
        FakePlanner(
            plan
        ),
        tool_backend=backend,
    )

    outcome = investigator.run(
        "¿De qué depende photo stack?"
    )

    assert (
        outcome.report.status
        == "ANSWERED"
    )

    assert (
        outcome.reason
        is None
    )

    assert (
        outcome.scope
        is not None
    )

    assert (
        outcome.scope.direction
        == "DOWNSTREAM"
    )

    assert backend.calls == [
        (
            "atlas_resolve_entity",
            {
                "query":
                    "photo stack",
            },
        ),
        (
            "atlas_query_entity_relations",
            {
                "entity":
                    "photo stack",

                "direction":
                    "downstream",

                "relationship":
                    "DEPENDS_ON",

                "depth":
                    1,
            },
        ),
    ]

    selected = (
        outcome.ledger.selected(
            outcome.report.fact_ids
        )
    )

    assert len(
        selected
    ) == 1

    assert (
        selected[0].kind
        == "RELATION"
    )

    assert (
        selected[0].subject_id
        == "application-alpha"
    )

    assert (
        selected[0].object_id
        == "dependency-alpha"
    )

    assert (
        "dependency-alpha"
        in outcome.answer
    )


def test_out_of_direction_relation_fails_closed():

    plan = InvestigationPlan(
        domain=EvidenceDomain.RELATION,
        target_query="photo stack",
        relationship="DEPENDS_ON",
        relation_anchor=(
            RelationAnchor.SUBJECT
        ),
    )

    backend = FakeToolBackend(
        {
            "atlas_resolve_entity":
                resolved_asset(),

            "atlas_query_entity_relations":
                FakeToolResult(
                    success=True,
                    data=relation_payload(
                        source_asset_id=(
                            "application-beta"
                        ),
                        target_asset_id=(
                            "application-alpha"
                        ),
                    ),
                ),
        }
    )

    outcome = AtlasInvestigator(
        FakePlanner(
            plan
        ),
        tool_backend=backend,
    ).run(
        "¿De qué depende photo stack?"
    )

    assert (
        outcome.report.status
        == "INSUFFICIENT_EVIDENCE"
    )

    assert (
        outcome.reason
        == "NO_IN_SCOPE_FACTS"
    )


def test_complete_zero_status_collection_is_answered():

    plan = InvestigationPlan(
        domain=EvidenceDomain.STATUS,
        scope_mode=(
            InvestigationScopeMode
            .COLLECTION
        ),
        collection_query="applications",
        asset_type="APPLICATION",
        status_filter="OFFLINE",
    )

    backend = FakeToolBackend(
        {
            "atlas_query_asset_status":
                FakeToolResult(
                    success=True,
                    data={
                        "status":
                            "SUCCESS",

                        "complete":
                            True,

                        "count":
                            0,

                        "filters":
                            {
                                "status":
                                    "OFFLINE",

                                "asset_type":
                                    "APPLICATION",

                                "criticality":
                                    None,

                                "role":
                                    None,
                            },

                        "assets":
                            [],

                        "evidence":
                            [
                                (
                                    "complete synthetic "
                                    "inventory query"
                                ),
                            ],
                    },
                ),
        }
    )

    outcome = AtlasInvestigator(
        FakePlanner(
            plan
        ),
        tool_backend=backend,
    ).run(
        "¿Qué aplicaciones están offline?"
    )

    assert (
        outcome.report.status
        == "ANSWERED"
    )

    assert outcome.report.fact_ids == [
        "FACT-001",
    ]

    fact = outcome.ledger.facts[
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

    assert fact.count == 0

    assert backend.calls == [
        (
            "atlas_query_asset_status",
            {
                "status":
                    "OFFLINE",

                "asset_type":
                    "APPLICATION",

                "criticality":
                    None,

                "role":
                    None,
            },
        ),
    ]

    assert (
        "no encontró"
        in outcome.answer
    )


def test_target_health_selects_only_direct_attention():

    plan = InvestigationPlan(
        domain=EvidenceDomain.HEALTH,
        target_query="application alpha",
    )

    backend = FakeToolBackend(
        {
            "atlas_resolve_entity":
                resolved_asset(),

            "atlas_attention_summary":
                FakeToolResult(
                    success=True,
                    data={
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
                                                "INC-ALPHA",

                                            "asset_id":
                                                (
                                                    "application-alpha"
                                                ),

                                            "severity":
                                                "HIGH",

                                            "status":
                                                "OPEN",

                                            "title":
                                                (
                                                    "Synthetic "
                                                    "degradation"
                                                ),

                                            "message":
                                                (
                                                    "Direct target "
                                                    "signal"
                                                ),
                                        },
                                        {
                                            "kind":
                                                "INCIDENT",

                                            "id":
                                                "INC-BETA",

                                            "asset_id":
                                                (
                                                    "application-beta"
                                                ),

                                            "severity":
                                                "HIGH",

                                            "status":
                                                "OPEN",

                                            "title":
                                                (
                                                    "Unrelated "
                                                    "degradation"
                                                ),

                                            "message":
                                                (
                                                    "Unrelated "
                                                    "signal"
                                                ),
                                        },
                                    ],
                            },
                    },
                ),
        }
    )

    outcome = AtlasInvestigator(
        FakePlanner(
            plan
        ),
        tool_backend=backend,
    ).run(
        "¿Tiene problemas application alpha?"
    )

    assert (
        outcome.report.status
        == "ANSWERED"
    )

    selected = (
        outcome.ledger.selected(
            outcome.report.fact_ids
        )
    )

    assert len(
        selected
    ) == 1

    assert (
        selected[0].signal_id
        == "INC-ALPHA"
    )

    assert (
        "INC-ALPHA"
        in outcome.answer
    )

    assert (
        "INC-BETA"
        not in outcome.answer
    )


def test_ambiguous_target_fails_closed_before_evidence_query():

    plan = InvestigationPlan(
        domain=EvidenceDomain.RELATION,
        target_query="shared service",
        relationship="DEPENDS_ON",
        relation_anchor=(
            RelationAnchor.SUBJECT
        ),
    )

    backend = FakeToolBackend(
        {
            "atlas_resolve_entity":
                FakeToolResult(
                    success=True,
                    data={
                        "status":
                            "SUCCESS",

                        "kind":
                            "AMBIGUOUS",

                        "candidates":
                            [
                                {
                                    "id":
                                        "asset-a",
                                },
                                {
                                    "id":
                                        "asset-b",
                                },
                            ],
                    },
                ),
        }
    )

    outcome = AtlasInvestigator(
        FakePlanner(
            plan
        ),
        tool_backend=backend,
    ).run(
        "¿De qué depende shared service?"
    )

    assert (
        outcome.report.status
        == "INSUFFICIENT_EVIDENCE"
    )

    assert (
        outcome.reason
        == "UNRESOLVED_TARGET"
    )

    assert backend.calls == [
        (
            "atlas_resolve_entity",
            {
                "query":
                    "shared service",
            },
        ),
    ]


def test_observation_and_target_status_remain_fail_closed():

    observation_plan = (
        InvestigationPlan(
            domain=(
                EvidenceDomain
                .OBSERVATION
            ),
            target_query="application alpha",
            observation="temperature",
        )
    )

    observation_backend = (
        FakeToolBackend(
            {}
        )
    )

    observation = (
        AtlasInvestigator(
            FakePlanner(
                observation_plan
            ),
            tool_backend=(
                observation_backend
            ),
        ).run(
            "temperature of application alpha"
        )
    )

    assert (
        observation.report.status
        == "INSUFFICIENT_EVIDENCE"
    )

    assert (
        observation.reason
        == "UNSUPPORTED_EVIDENCE_DOMAIN"
    )

    assert (
        observation_backend.calls
        == []
    )

    target_status_plan = (
        InvestigationPlan(
            domain=(
                EvidenceDomain.STATUS
            ),
            target_query="application alpha",
        )
    )

    status_backend = (
        FakeToolBackend(
            {}
        )
    )

    target_status = (
        AtlasInvestigator(
            FakePlanner(
                target_status_plan
            ),
            tool_backend=status_backend,
        ).run(
            "status of application alpha"
        )
    )

    assert (
        target_status.report.status
        == "INSUFFICIENT_EVIDENCE"
    )

    assert (
        target_status.reason
        == "TARGET_STATUS_NOT_SUPPORTED"
    )

    assert status_backend.calls == []
