from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from atlas.services.ai.investigator.contracts import (
    InvestigationReport,
)
from atlas.services.ai.investigator.evidence import (
    EvidenceLedger,
)
from atlas.services.ai.investigator.planning import (
    InvestigationPlan,
    build_investigation_scope,
)
from atlas.services.ai.investigator.rendering import (
    render_report,
)
from atlas.services.ai.investigator.scope import (
    EvidenceDomain,
    InvestigationScope,
    InvestigationScopeMode,
    validate_fact_selection,
)


@dataclass
class InvestigationOutcome:
    """
    Complete result of one verified ATLAS investigation.

    The outcome intentionally exposes the plan, deterministic scope,
    evidence ledger and final report so callers and tests can audit the
    complete authority chain.

    Infrastructure facts always come from EvidenceLedger.
    """

    plan: InvestigationPlan

    scope: InvestigationScope | None

    ledger: EvidenceLedger

    report: InvestigationReport

    answer: str

    reason: str | None = None


class AtlasInvestigator:
    """
    Deterministic executor for a typed InvestigationPlan.

    Authority boundaries:

        planner
            interprets user intent

        ATLAS scope builder
            decides which evidence is allowed

        atlas-knowledge MCP
            retrieves read-only ATLAS knowledge

        EvidenceLedger
            converts tool results into canonical VerifiedFact objects

        validate_fact_selection()
            enforces scope and fact-chain validity

        InvestigationReport
            selects verified fact identifiers only

    The investigator does not let the LLM choose tools freely and does
    not let the LLM author infrastructure facts.
    """

    def __init__(
        self,
        planner,
        *,
        tool_backend=None,
    ):

        self.planner = planner

        if tool_backend is None:

            from atlas.mcp.client import (
                MCPKnowledgeClient,
            )

            tool_backend = (
                MCPKnowledgeClient()
            )

        self.tool_backend = (
            tool_backend
        )


    @staticmethod
    def _insufficient_report(
    ) -> InvestigationReport:

        return InvestigationReport(
            status=(
                "INSUFFICIENT_EVIDENCE"
            ),
        )


    @classmethod
    def _insufficient(
        cls,
        *,
        plan: InvestigationPlan,
        scope: InvestigationScope | None,
        ledger: EvidenceLedger,
        reason: str,
    ) -> InvestigationOutcome:

        report = (
            cls._insufficient_report()
        )

        return InvestigationOutcome(
            plan=plan,
            scope=scope,
            ledger=ledger,
            report=report,
            answer=render_report(
                report,
                ledger,
            ),
            reason=reason,
        )


    def _execute_tool(
        self,
        ledger: EvidenceLedger,
        name: str,
        **kwargs,
    ) -> tuple[
        Any | None,
        str | None,
    ]:
        """
        Execute one allowlisted read-only knowledge tool.

        Tool exceptions and failed MCP results fail closed. They never
        become infrastructure evidence.
        """

        ledger.record_tool_call(
            name
        )

        try:

            result = (
                self.tool_backend
                .execute_tool(
                    name,
                    **kwargs,
                )
            )

        except Exception as exc:

            return (
                None,
                (
                    "TOOL_EXCEPTION:"
                    f"{type(exc).__name__}"
                ),
            )

        success = bool(
            getattr(
                result,
                "success",
                False,
            )
        )

        if not success:

            error = getattr(
                result,
                "error",
                None,
            )

            return (
                None,
                str(
                    error
                    or "MCP_TOOL_FAILED"
                ),
            )

        return (
            getattr(
                result,
                "data",
                None,
            ),
            None,
        )


    @classmethod
    def _resolution_asset_ids(
        cls,
        data,
    ) -> set[str]:
        """
        Extract canonical asset identifiers from an ATLAS entity
        resolution result.

        This adapter is intentionally conservative.

        It accepts explicit asset/member containers and recursively
        follows known semantic-result containers. It never interprets
        arbitrary text or candidate names as canonical assets.

        AMBIGUOUS, NOT_FOUND and ERROR resolutions fail closed.
        """

        if not isinstance(
            data,
            dict,
        ):
            return set()

        terminal_tokens = set()

        for key in (
            "status",
            "kind",
            "entity_type",
            "resolution_type",
            "resolution_status",
        ):

            value = data.get(
                key
            )

            if value is None:
                continue

            terminal_tokens.add(
                str(
                    value
                ).strip().upper()
            )

        resolution_value = (
            data.get(
                "resolution"
            )
        )

        if isinstance(
            resolution_value,
            str,
        ):

            terminal_tokens.add(
                resolution_value
                .strip()
                .upper()
            )

        if terminal_tokens & {
            "AMBIGUOUS",
            "NOT_FOUND",
            "NOTFOUND",
            "ERROR",
            "FAILED",
        }:

            return set()

        asset_ids: set[str] = set()

        def add_id(
            value,
        ) -> None:

            if value is None:
                return

            normalized = str(
                value
            ).strip()

            if normalized:
                asset_ids.add(
                    normalized
                )

        #
        # Explicit canonical asset identifier.
        #
        add_id(
            data.get(
                "asset_id"
            )
        )

        kind = str(
            data.get(
                "kind"
            )
            or data.get(
                "entity_type"
            )
            or data.get(
                "resolution_type"
            )
            or (
                resolution_value
                if isinstance(
                    resolution_value,
                    str,
                )
                else ""
            )
            or ""
        ).strip().upper()

        #
        # A generic "id" is accepted only when ATLAS explicitly says
        # that the resolved entity is an ASSET.
        #
        if kind == "ASSET":

            add_id(
                data.get(
                    "id"
                )
            )

        #
        # Explicit collections of canonical asset identifiers.
        #
        for key in (
            "asset_ids",
            "member_ids",
            "member_asset_ids",
            "target_asset_ids",
        ):

            values = data.get(
                key
            )

            if not isinstance(
                values,
                (
                    list,
                    tuple,
                    set,
                ),
            ):
                continue

            for value in values:

                if isinstance(
                    value,
                    dict,
                ):

                    add_id(
                        value.get(
                            "asset_id"
                        )
                        or value.get(
                            "id"
                        )
                    )

                else:

                    add_id(
                        value
                    )

        #
        # Semantic groups commonly expose members/assets as structured
        # objects. IDs inside those explicit containers are safe to use
        # as scope targets.
        #
        for key in (
            "members",
            "assets",
        ):

            values = data.get(
                key
            )

            if not isinstance(
                values,
                (
                    list,
                    tuple,
                    set,
                ),
            ):
                continue

            for value in values:

                if isinstance(
                    value,
                    dict,
                ):

                    add_id(
                        value.get(
                            "asset_id"
                        )
                        or value.get(
                            "id"
                        )
                    )

                else:

                    add_id(
                        value
                    )

        #
        # Follow only known structural containers.
        #
        for key in (
            "entity",
            "asset",
            "resolved",
            "resolved_entity",
            "result",
            "resolution",
            "data",
        ):

            nested = data.get(
                key
            )

            if not isinstance(
                nested,
                dict,
            ):
                continue

            asset_ids.update(
                cls._resolution_asset_ids(
                    nested
                )
            )

        return asset_ids


    def _resolve_target(
        self,
        ledger: EvidenceLedger,
        target_query: str,
    ) -> tuple[
        set[str],
        str | None,
    ]:

        data, error = (
            self._execute_tool(
                ledger,
                "atlas_resolve_entity",
                query=target_query,
            )
        )

        if error is not None:

            return (
                set(),
                "TARGET_RESOLUTION_FAILED",
            )

        asset_ids = (
            self._resolution_asset_ids(
                data
            )
        )

        if not asset_ids:

            return (
                set(),
                "UNRESOLVED_TARGET",
            )

        return (
            asset_ids,
            None,
        )


    @staticmethod
    def _tool_request(
        plan: InvestigationPlan,
        scope: InvestigationScope,
    ) -> tuple[
        str,
        dict[str, Any],
    ] | None:
        """
        Deterministically map an approved scope to one read-only
        atlas-knowledge query.

        The model never supplies a tool name.
        """

        if (
            scope.domain
            == EvidenceDomain.RELATION
        ):

            if (
                not plan.target_query
                or not scope.relationship
                or not scope.direction
            ):
                return None

            return (
                "atlas_query_entity_relations",
                {
                    "entity":
                        plan.target_query,

                    "direction":
                        scope.direction
                        .lower(),

                    "relationship":
                        scope.relationship,

                    "depth":
                        1,
                },
            )

        if (
            scope.domain
            == EvidenceDomain.STATUS
        ):

            return (
                "atlas_query_asset_status",
                {
                    "status":
                        scope.status_filter,

                    "asset_type":
                        scope.asset_type,

                    "criticality":
                        scope.criticality,

                    "role":
                        scope.role,
                },
            )

        if (
            scope.domain
            in {
                EvidenceDomain.ATTENTION,
                EvidenceDomain.HEALTH,
            }
        ):

            return (
                "atlas_attention_summary",
                {},
            )

        return None


    def run(
        self,
        question: str,
    ) -> InvestigationOutcome:
        """
        Execute one complete verified investigation.

        V1 supports:

            RELATION
            ATTENTION
            HEALTH
            STATUS in GLOBAL/COLLECTION scope

        OBSERVATION remains fail-closed until ATLAS has a canonical
        ObservationFact ingestion contract.

        TARGET STATUS also remains fail-closed in V1. The current
        status MCP query is an inventory query; using its global count
        as though it represented a single resolved target would be
        semantically incorrect.
        """

        normalized = str(
            question
            or ""
        ).strip()

        if not normalized:

            raise ValueError(
                "Investigation question "
                "cannot be empty."
            )

        plan = self.planner.plan(
            normalized
        )

        ledger = EvidenceLedger()

        #
        # Fail closed before making knowledge calls for domains that do
        # not yet have a verified fact contract.
        #
        if (
            plan.domain
            in {
                EvidenceDomain.UNKNOWN,
                EvidenceDomain.OBSERVATION,
            }
        ):

            return self._insufficient(
                plan=plan,
                scope=None,
                ledger=ledger,
                reason=(
                    "UNSUPPORTED_EVIDENCE_DOMAIN"
                ),
            )

        #
        # A target-specific STATUS answer needs a target-specific
        # authoritative query contract. The current inventory tool does
        # not provide that contract.
        #
        if (
            plan.domain
            == EvidenceDomain.STATUS
            and plan.scope_mode
            == InvestigationScopeMode.TARGET
        ):

            return self._insufficient(
                plan=plan,
                scope=None,
                ledger=ledger,
                reason=(
                    "TARGET_STATUS_NOT_SUPPORTED"
                ),
            )

        target_asset_ids: set[str] = set()

        if (
            plan.scope_mode
            == InvestigationScopeMode.TARGET
        ):

            target_asset_ids, error = (
                self._resolve_target(
                    ledger,
                    plan.target_query
                    or "",
                )
            )

            if error is not None:

                return self._insufficient(
                    plan=plan,
                    scope=None,
                    ledger=ledger,
                    reason=error,
                )

        built = build_investigation_scope(
            plan,
            target_asset_ids=(
                target_asset_ids
            ),
        )

        if (
            built.status
            != "SUCCESS"
            or built.scope
            is None
        ):

            return self._insufficient(
                plan=plan,
                scope=None,
                ledger=ledger,
                reason=(
                    built.reason
                    or built.status
                ),
            )

        scope = built.scope

        request = (
            self._tool_request(
                plan,
                scope,
            )
        )

        if request is None:

            return self._insufficient(
                plan=plan,
                scope=scope,
                ledger=ledger,
                reason=(
                    "NO_VERIFIED_TOOL_ROUTE"
                ),
            )

        (
            tool_name,
            tool_arguments,
        ) = request

        data, error = (
            self._execute_tool(
                ledger,
                tool_name,
                **tool_arguments,
            )
        )

        if error is not None:

            return self._insufficient(
                plan=plan,
                scope=scope,
                ledger=ledger,
                reason="EVIDENCE_TOOL_FAILED",
            )

        try:

            fact_ids = ledger.ingest(
                tool_name,
                data,
            )

        except Exception:

            return self._insufficient(
                plan=plan,
                scope=scope,
                ledger=ledger,
                reason=(
                    "EVIDENCE_INGEST_FAILED"
                ),
            )

        if not fact_ids:

            #
            # Important:
            #
            # RELATION V1 has no RelationQueryFact equivalent to
            # StatusQueryFact. Therefore zero returned relationships
            # cannot yet be represented as verified negative evidence.
            #
            return self._insufficient(
                plan=plan,
                scope=scope,
                ledger=ledger,
                reason=(
                    "NO_VERIFIED_FACTS"
                ),
            )

        validation = (
            validate_fact_selection(
                scope,
                ledger,
                fact_ids,
            )
        )

        accepted = list(
            validation
            .accepted_fact_ids
        )

        if not accepted:

            return self._insufficient(
                plan=plan,
                scope=scope,
                ledger=ledger,
                reason=(
                    "NO_IN_SCOPE_FACTS"
                ),
            )

        report = InvestigationReport(
            status="ANSWERED",
            fact_ids=accepted,
        )

        return InvestigationOutcome(
            plan=plan,
            scope=scope,
            ledger=ledger,
            report=report,
            answer=render_report(
                report,
                ledger,
            ),
            reason=None,
        )
