from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path


# =============================================================================
# MAKE ATLAS CORE AVAILABLE TO THE ISOLATED INVESTIGATOR VENV
# =============================================================================

ROOT = Path(
    __file__
).resolve().parents[1]

SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(
        0,
        str(SRC),
    )


# =============================================================================
# INVESTIGATOR RUNTIME DEPENDENCIES
# =============================================================================

from fastmcp import (
    Client,
)
from fastmcp.client.transports import (
    StdioTransport,
)

from pydantic_ai import (
    Agent,
    ModelRetry,
    RunContext,
    UsageLimitExceeded,
)
from pydantic_ai.mcp import (
    CallToolFunc,
    MCPToolset,
    ToolResult,
)
from pydantic_ai.models.ollama import (
    OllamaModel,
)
from pydantic_ai.providers.ollama import (
    OllamaProvider,
)
from pydantic_ai.settings import (
    ModelSettings,
)
from pydantic_ai.usage import (
    UsageLimits,
)


# =============================================================================
# ATLAS INVESTIGATION CORE
# =============================================================================

from atlas.core.asset import (
    AssetRole,
    AssetStatus,
    AssetType,
    Criticality,
)

from atlas.services.ai.investigator import (
    EvidenceDomain,
    EvidenceLedger,
    InvestigationPlan,
    InvestigationReport,
    InvestigationScope,
    InvestigationScopeMode,
    build_investigation_scope,
    render_report,
    validate_fact_selection,
)


# =============================================================================
# CONFIGURATION
# =============================================================================

ATLAS_PYTHON = Path(
    os.environ.get(
        "ATLAS_RUNTIME_PYTHON",
        ROOT / ".venv/bin/python",
    )
)

OLLAMA_BASE_URL = os.environ.get(
    "OLLAMA_BASE_URL",
    "",
).strip()

MODEL_NAME = os.environ.get(
    "ATLAS_INVESTIGATOR_MODEL",
    "",
).strip()


SYSTEM_INSTRUCTIONS = """
You are Atlas Investigator, a read-only infrastructure investigator.

ATLAS is the only authoritative source of infrastructure facts.

Investigation rules:
- Use ATLAS tools to investigate the user's question.
- Prefer semantic entity resolution for human-readable concepts.
- When ATLAS resolves a concept as a GROUP, use group-aware semantic tools.
- Investigate minimally and stop when sufficient evidence exists.
- Never invent infrastructure facts.
- Never use general product knowledge as infrastructure evidence.
- Never invert relationship direction.
- Never execute infrastructure changes.

Final-output rules:
- Your final output MUST be an InvestigationReport.
- Do not write a natural-language answer.
- For ANSWERED, select only FACT identifiers explicitly returned as
  verified_fact_ids by ATLAS tool results.
- When verified_fact_ids directly support the user's question, select the
  relevant identifiers and return ANSWERED.
- Never invent a FACT identifier.
- If ATLAS does not provide sufficient verified facts, return
  INSUFFICIENT_EVIDENCE.
""".strip()



PLANNING_INSTRUCTIONS = f"""
You are the planning stage of Atlas Investigator.

You do not have infrastructure tools and you do not know infrastructure facts.

Your only task is to classify what evidence would be required to answer the
user's question and return a structured InvestigationPlan.

Evidence domains:
- RELATION: relationships between infrastructure entities.
- ATTENTION: current operational signals requiring attention.
- STATUS: current canonical ATLAS asset state.
- OBSERVATION: measured values, telemetry or observations.
- IMPACT: consequences or affected entities.
- HEALTH: whether a specific entity has operational problems or degradation.
- UNKNOWN: the evidence domain itself cannot be determined safely.

UNKNOWN must not be used merely because a named entity may not exist.
Entity existence is determined later by ATLAS target resolution.

For domains other than RELATION:
- relationship must be null
- relation_anchor must be null

For STATUS:

STATUS uses canonical ATLAS inventory selectors.

Canonical asset_type values:
{", ".join(item.name for item in AssetType)}

Canonical role values:
{", ".join(item.name for item in AssetRole)}

Canonical criticality values:
{", ".join(item.name for item in Criticality)}

Canonical status_filter values:
{", ".join(item.name for item in AssetStatus)}

STATUS scope semantics:

- TARGET:
  The question asks for the current state of one concrete entity.
  Set target_query to that entity.
  Set collection_query=null.
  Set asset_type=null.
  Set role=null.
  Set criticality=null.
  Set status_filter=null.
  Do not assume the entity's state from wording in the question.

- COLLECTION:
  The question asks for members of a semantic population or category.
  Set collection_query to the human-readable population.
  Set target_query=null.
  Translate the population into at least one canonical selector:
  asset_type, role or criticality.
  If the user asks for members matching a particular current state,
  set status_filter to the corresponding canonical AssetStatus value.

- GLOBAL:
  The question asks across the entire infrastructure.
  Set target_query=null.
  Set collection_query=null.
  Set asset_type=null.
  Set role=null.
  Set criticality=null.
  status_filter may contain the canonical state requested by the user.

Do not invent selector values.
Use only the canonical ATLAS ontology values listed above.

For domains other than STATUS:
- asset_type must be null
- role must be null
- criticality must be null
- status_filter must be null

For OBSERVATION:
- target_query is the human-readable infrastructure entity being measured.
- observation is the measured attribute, telemetry value or observation
  requested by the user.
- A question asking for one measurement of one described entity uses
  scope_mode=TARGET and target_query is that entity.
- A question requesting measurements for a category uses
  scope_mode=COLLECTION and collection_query is that category.
- A question requesting measurements across the whole infrastructure uses
  scope_mode=GLOBAL.
- Do not combine the entity and measurement into target_query.

For domains other than OBSERVATION:
- observation must be null.

For RELATION, reason using the canonical relationship form:

    SUBJECT --RELATIONSHIP--> OBJECT

- target_query is only the human-readable infrastructure entity being asked
  about.
- relationship is the canonical relationship predicate when known.
- relation_anchor describes where target_query appears in that canonical
  relationship.
- relation_anchor=SUBJECT when the target is the relationship subject.
- relation_anchor=OBJECT when the target is the relationship object.
- Do not produce graph traversal direction. ATLAS derives direction
  deterministically from relation_anchor.

For example, with the canonical relation:

    A DEPENDS_ON B

A question asking what A depends on has:
- target_query=A
- relationship=DEPENDS_ON
- relation_anchor=SUBJECT

A question asking what depends on B has:
- target_query=B
- relationship=DEPENDS_ON
- relation_anchor=OBJECT

Scope cardinality rule — apply this before choosing scope_mode:

scope_mode describes HOW MANY infrastructure entities the user's question
refers to. It is not determined by whether the target words can also name
an asset category.

- TARGET means the question refers to one entity.
  A human-readable singular or definite description may be TARGET even when
  it is not a proper name, canonical id or globally unique identifier.
  ATLAS resolves existence and ambiguity later.
  Do not convert a singular entity reference into COLLECTION merely because
  its words could also describe an asset type or category.

- COLLECTION means the question explicitly refers to multiple entities or to
  a category/population as a set.

- GLOBAL means the question concerns the infrastructure as a whole.

Choose exactly one semantic scope_mode:

- TARGET: the question is about one concrete infrastructure entity.
  Set target_query to that entity and collection_query=null.

- COLLECTION: the question asks about a population or category of
  infrastructure entities.
  Set collection_query to the human-readable population and
  target_query=null.

- GLOBAL: the question is about the infrastructure as a whole.
  Set target_query=null and collection_query=null.

Examples of scope semantics:
- one named server or application -> TARGET
- applications, servers, databases, devices as a population -> COLLECTION
- the whole infrastructure -> GLOBAL

Do not output global_scope. ATLAS derives it deterministically from scope_mode.

target_query must refer to one infrastructure entity as expressed by the user,
not to a population and not to the requested evidence attribute.
It does not need to be a proper name or canonical identifier. A singular
human-readable description may be a TARGET; ATLAS performs entity resolution
later.

Do not invent infrastructure identifiers.
Do not decide whether an entity exists.
Do not answer the user's question.
Do not investigate.
Return only the structured InvestigationPlan.
""".strip()


def build_runtime_transport() -> StdioTransport:

    return StdioTransport(
        command=str(
            ATLAS_PYTHON
        ),
        args=[
            "-m",
            "atlas.mcp.server",
        ],
        cwd=str(
            ROOT
        ),
    )


def structured_tool_result(
    result,
) -> dict:

    structured = getattr(
        result,
        "structured_content",
        None,
    )

    if isinstance(
        structured,
        dict,
    ):
        return structured

    data = getattr(
        result,
        "data",
        None,
    )

    if isinstance(
        data,
        dict,
    ):
        return data

    if isinstance(
        result,
        dict,
    ):
        return result

    model_dump = getattr(
        result,
        "model_dump",
        None,
    )

    if callable(
        model_dump
    ):

        value = model_dump(
            mode="json"
        )

        if isinstance(
            value,
            dict,
        ):
            return value

    return {}


def atlas_tool_data(
    result,
) -> dict:

    raw = structured_tool_result(
        result
    )

    data = raw.get(
        "data"
    )

    if isinstance(
        data,
        dict,
    ):
        return data

    return raw


async def create_investigation_plan(
    question: str,
    model,
):

    planner = Agent(
        model=model,
        output_type=InvestigationPlan,
        instructions=PLANNING_INSTRUCTIONS,
        model_settings=ModelSettings(
            max_tokens=1024,
            temperature=0.0,
        ),
        retries=2,
    )

    result = await planner.run(
        question
    )

    return (
        result.output,
        result.usage,
    )


async def resolve_plan_scope(
    plan: InvestigationPlan,
):

    # UNKNOWN has no trustworthy evidence contract.
    if (
        plan.domain
        == EvidenceDomain.UNKNOWN
    ):

        return (
            None,
            None,
            "UNKNOWN_DOMAIN",
        )

    # GLOBAL and COLLECTION investigations require no concrete
    # entity resolution.
    if (
        plan.scope_mode
        in {
            InvestigationScopeMode.GLOBAL,
            InvestigationScopeMode.COLLECTION,
        }
    ):

        built = build_investigation_scope(
            plan
        )

        return (
            built.scope,
            None,
            built.status,
        )

    if (
        plan.scope_mode
        != InvestigationScopeMode.TARGET
    ):

        return (
            None,
            None,
            "INVALID_SCOPE_MODE",
        )

    if not plan.target_query:

        return (
            None,
            None,
            "MISSING_TARGET",
        )

    transport = build_runtime_transport()

    print(
        "\n[ATLAS PREFLIGHT]",
        "atlas_resolve_entity",
        json.dumps(
            {
                "query":
                    plan.target_query,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    async with Client(
        transport
    ) as client:

        result = await client.call_tool(
            "atlas_resolve_entity",
            {
                "query":
                    plan.target_query,
            },
        )

    data = atlas_tool_data(
        result
    )

    print(
        "[ATLAS PREFLIGHT STATUS]",
        data.get(
            "status"
        ),
        flush=True,
    )

    if (
        data.get(
            "status"
        )
        != "SUCCESS"
    ):

        return (
            None,
            None,
            str(
                data.get(
                    "status"
                )
                or "UNRESOLVED_TARGET"
            ),
        )

    entity = data.get(
        "entity"
    )

    if not isinstance(
        entity,
        dict,
    ):

        return (
            None,
            None,
            "INVALID_ENTITY_RESULT",
        )

    kind = str(
        entity.get(
            "kind"
        )
        or ""
    ).strip().upper()

    if kind not in {
        "ASSET",
        "GROUP",
    }:

        return (
            None,
            None,
            kind
            or "UNRESOLVED_TARGET",
        )

    targets = {
        str(item).strip()
        for item in (
            entity.get(
                "member_ids"
            )
            or []
        )
        if str(item).strip()
    }

    asset_id = entity.get(
        "asset_id"
    )

    if asset_id:

        targets.add(
            str(
                asset_id
            ).strip()
        )

    built = build_investigation_scope(
        plan,
        target_asset_ids=targets,
    )

    if (
        built.status
        != "SUCCESS"
        or built.scope is None
    ):

        return (
            None,
            None,
            built.status,
        )

    reference = entity.get(
        "reference"
    )

    return (
        built.scope,
        (
            str(reference).strip()
            if reference
            else None
        ),
        "SUCCESS",
    )


def build_investigator_instructions(
    plan: InvestigationPlan,
    scope: InvestigationScope,
    resolved_reference: str | None,
) -> str:

    reference_text = (
        resolved_reference
        or "none"
    )

    return (
        SYSTEM_INSTRUCTIONS
        + """

The investigation plan was fixed before evidence collection.
It is authoritative for evidence relevance and cannot be changed.

INVESTIGATION PLAN:
"""
        + plan.model_dump_json(
            indent=2
        )
        + """

ATLAS EVIDENCE SCOPE:
"""
        + scope.model_dump_json(
            indent=2
        )
        + f"""

CANONICAL TARGET REFERENCE:
{reference_text}

Additional rules:
- Select only facts that directly support this fixed investigation plan.
- The final validator rejects facts outside the fixed ATLAS evidence scope.
- If no in-scope verified evidence exists, return INSUFFICIENT_EVIDENCE.
- Do not reinterpret the question after seeing evidence.
- Do not broaden the investigation domain to justify available facts.
"""
        + (
            """
- ATLAS already resolved the target.
- For semantic relationship queries, use the canonical target reference above
  directly instead of resolving the human-readable target again.
"""
            if resolved_reference
            else ""
        )
        + (
            """
- For STATUS evidence, atlas_query_asset_status returns a STATUS_QUERY fact
  plus zero or more STATUS asset facts.
- A complete STATUS_QUERY fact is required to support a STATUS answer.
- When the verified query count is zero, the STATUS_QUERY fact alone is
  sufficient verified negative evidence.
- When assets match, select the STATUS_QUERY fact and the relevant linked
  STATUS facts together.
"""
            if plan.domain
            == EvidenceDomain.STATUS
            else ""
        )
    )



# =============================================================================
# PLAN-SCOPED TOOL EXPOSURE
# =============================================================================

DOMAIN_TOOL_POLICY = {

    EvidenceDomain.RELATION:
        frozenset(
            {
                "atlas_query_entity_relations",
            }
        ),

    EvidenceDomain.ATTENTION:
        frozenset(
            {
                "atlas_attention_summary",
            }
        ),

    EvidenceDomain.STATUS:
        frozenset(
            {
                "atlas_query_asset_status",
            }
        ),

    # HEALTH currently has one verified evidence source:
    # direct operational attention attached to an asset in scope.
    #
    # Asset status/health and impact evidence will be exposed only
    # after the EvidenceLedger has canonical fact types for them.
    EvidenceDomain.HEALTH:
        frozenset(
            {
                "atlas_attention_summary",
            }
        ),
}


def allowed_tools_for_plan(
    plan: InvestigationPlan,
) -> frozenset[str]:

    # --------------------------------------------------------------
    # STATUS TARGET is intentionally not exposed yet.
    #
    # The current verified status capability queries structured
    # inventory dimensions. It does not yet constrain a query to one
    # canonical resolved asset id.
    # --------------------------------------------------------------

    if (
        plan.domain
        == EvidenceDomain.STATUS
        and plan.scope_mode
        == InvestigationScopeMode.TARGET
    ):

        return frozenset()

    return DOMAIN_TOOL_POLICY.get(
        plan.domain,
        frozenset(),
    )


class NoInScopeEvidenceError(RuntimeError):
    """
    The tool returned verified ATLAS facts, but none are admissible
    under the fixed deterministic investigation scope.

    Facts remain in the EvidenceLedger for auditability.
    """

    def __init__(
        self,
        reasons: dict[str, str],
    ) -> None:

        self.reasons = dict(
            reasons
        )

        super().__init__(
            "No verified facts from the tool call "
            "are inside the fixed investigation scope."
        )


# =============================================================================
# CONFIG VALIDATION
# =============================================================================

def validate_configuration() -> None:

    if not ATLAS_PYTHON.exists():

        raise SystemExit(
            "ATLAS runtime Python not found: "
            f"{ATLAS_PYTHON}"
        )

    if not OLLAMA_BASE_URL:

        raise SystemExit(
            "OLLAMA_BASE_URL is required."
        )

    if not MODEL_NAME:

        raise SystemExit(
            "ATLAS_INVESTIGATOR_MODEL is required."
        )


# =============================================================================
# TOOL ADAPTER
# =============================================================================

async def verified_tool_call(
    ctx: RunContext[
        EvidenceLedger
    ],
    call_tool: CallToolFunc,
    name: str,
    tool_args: dict,
) -> ToolResult:

    ledger = ctx.deps

    ledger.record_tool_call(
        name
    )

    print(
        "\n[ATLAS TOOL]",
        name,
        json.dumps(
            tool_args,
            ensure_ascii=False,
            default=str,
        ),
        flush=True,
    )

    result = await call_tool(
        name,
        tool_args,
    )

    print(
        "[ATLAS TOOL OK]",
        name,
        flush=True,
    )

    fact_ids = ledger.ingest(
        name,
        result,
    )

    for fact_id in fact_ids:

        fact = ledger.facts[
            fact_id
        ]

        if fact.kind == "RELATION":

            print(
                "[LEDGER]",
                fact.id,
                fact.subject_id,
                fact.predicate,
                fact.object_id,
                flush=True,
            )

        elif fact.kind == "ATTENTION":

            print(
                "[LEDGER]",
                fact.id,
                "ATTENTION",
                fact.signal_kind,
                fact.signal_id,
                fact.severity,
                flush=True,
            )

    # The original ATLAS result remains the evidence.
    # FACT IDs are only references into the verified ledger.
    if (
        fact_ids
        and isinstance(
            result,
            dict,
        )
    ):

        result = dict(
            result
        )

        result[
            "verified_fact_ids"
        ] = fact_ids

    preview = repr(
        result
    )

    if len(preview) > 2500:

        preview = (
            preview[:2500]
            + "... <truncated>"
        )

    print(
        "[ATLAS EVIDENCE]",
        preview,
        flush=True,
    )

    return result


# =============================================================================
# OUTPUT VALIDATION
# =============================================================================

def register_output_validator(
    agent: Agent,
    scope: InvestigationScope,
) -> None:

    @agent.output_validator
    def validate_report(
        ctx: RunContext[
            EvidenceLedger
        ],
        report: InvestigationReport,
    ) -> InvestigationReport:

        ledger = ctx.deps

        if report.status == "ANSWERED":

            if not report.fact_ids:

                raise ModelRetry(
                    "ANSWERED requires at least one "
                    "verified FACT identifier."
                )

            unknown = ledger.validate_fact_ids(
                report.fact_ids
            )

            if unknown:

                available = sorted(
                    ledger.facts
                )

                raise ModelRetry(
                    "Unsupported FACT identifiers: "
                    f"{unknown}. "
                    "Use only verified FACT identifiers "
                    f"available in this run: {available}."
                )

            scoped = validate_fact_selection(
                scope,
                ledger,
                report.fact_ids,
            )

            if scoped.rejected_fact_ids:

                print(
                    "\n[SCOPE REJECT]",
                    {
                        fact_id:
                            scoped.reasons.get(
                                fact_id
                            )
                        for fact_id
                        in scoped.rejected_fact_ids
                    },
                    flush=True,
                )

                raise ModelRetry(
                    "Some selected FACT identifiers are "
                    "outside the fixed investigation scope: "
                    f"{scoped.reasons}. "
                    "Select only in-scope verified facts. "
                    "If no in-scope verified facts exist, "
                    "return INSUFFICIENT_EVIDENCE."
                )

        elif (
            report.status
            == "INSUFFICIENT_EVIDENCE"
            and not ledger.tool_calls
        ):

            # This is allowed only when target resolution or planning
            # failed before the investigator runs. Once the investigator
            # is active, it must inspect ATLAS before giving up.
            raise ModelRetry(
                "Investigate ATLAS before declaring "
                "insufficient evidence."
            )

        return report


# =============================================================================
# DEBUG OUTPUT
# =============================================================================

def print_report(
    report: InvestigationReport,
    ledger: EvidenceLedger,
) -> None:

    print()
    print("=" * 80)
    print("STRUCTURED REPORT")
    print("=" * 80)

    print(
        report.model_dump_json(
            indent=2,
        )
    )

    print()
    print("=" * 80)
    print("VERIFIED LEDGER")
    print("=" * 80)

    for fact in ledger.facts.values():

        print(
            fact.model_dump_json()
        )

    print()
    print("=" * 80)
    print("ANSWER")
    print("=" * 80)

    print(
        render_report(
            report,
            ledger,
        )
    )


# =============================================================================
# INVESTIGATION
# =============================================================================

async def investigate(
    question: str,
) -> None:

    ledger = EvidenceLedger()

    model = OllamaModel(
        MODEL_NAME,
        provider=OllamaProvider(
            base_url=OLLAMA_BASE_URL,
        ),
    )

    print("=" * 80)
    print("ATLAS SCOPED VERIFIED INVESTIGATOR")
    print("=" * 80)
    print("MODEL:", MODEL_NAME)
    print("QUESTION:", question)
    print()

    # --------------------------------------------------------------
    # PHASE 1 — PLAN WITHOUT TOOLS
    # --------------------------------------------------------------

    plan, plan_usage = (
        await create_investigation_plan(
            question,
            model,
        )
    )

    print("=" * 80)
    print("INVESTIGATION PLAN")
    print("=" * 80)
    print(
        plan.model_dump_json(
            indent=2,
        )
    )

    print()
    print(
        "[PLAN USAGE]",
        plan_usage,
    )

    # --------------------------------------------------------------
    # PHASE 2 — DETERMINISTIC TARGET RESOLUTION + FIXED SCOPE
    # --------------------------------------------------------------

    (
        scope,
        resolved_reference,
        scope_status,
    ) = await resolve_plan_scope(
        plan
    )

    if scope is None:

        print()
        print(
            "[SCOPE BUILD FAILED]",
            scope_status,
        )

        report = InvestigationReport(
            status="INSUFFICIENT_EVIDENCE",
            fact_ids=[],
        )

        print_report(
            report,
            ledger,
        )

        return

    print()
    print("=" * 80)
    print("FIXED INVESTIGATION SCOPE")
    print("=" * 80)
    print(
        scope.model_dump_json(
            indent=2,
        )
    )

    if resolved_reference:

        print(
            "REFERENCE:",
            resolved_reference,
        )

    # --------------------------------------------------------------
    # PHASE 3 — TOOL-BASED INVESTIGATION
    # --------------------------------------------------------------

    allowed_tools = allowed_tools_for_plan(
        plan
    )

    print()
    print(
        "[TOOL SCOPE]",
        sorted(
            allowed_tools
        ),
        flush=True,
    )

    # --------------------------------------------------------------
    # Fail closed when ATLAS does not yet have a verified Fact
    # contract for this evidence domain.
    # --------------------------------------------------------------

    if not allowed_tools:

        print(
            "[UNSUPPORTED EVIDENCE DOMAIN]",
            plan.domain.value,
            flush=True,
        )

        report = InvestigationReport(
            status="INSUFFICIENT_EVIDENCE",
            fact_ids=[],
        )

        print_report(
            report,
            ledger,
        )

        return

    transport = build_runtime_transport()

    # --------------------------------------------------------------
    # The fixed InvestigationPlan is authoritative for semantic
    # arguments that have already been decided before investigation.
    #
    # The LLM may decide WHEN evidence is needed, but it must not
    # silently broaden or contradict the approved plan.
    # --------------------------------------------------------------

    async def planned_verified_tool_call(
        ctx: RunContext[
            EvidenceLedger
        ],
        call_tool: CallToolFunc,
        name: str,
        tool_args: dict,
    ) -> ToolResult:

        planned_args = dict(
            tool_args
        )

        if (
            plan.domain
            == EvidenceDomain.RELATION
            and name
            == "atlas_query_entity_relations"
        ):

            if plan.relationship:

                planned_args[
                    "relationship"
                ] = plan.relationship

            if plan.direction:

                planned_args[
                    "direction"
                ] = (
                    plan.direction
                    .value
                    .lower()
                )

        if (
            plan.domain
            == EvidenceDomain.STATUS
            and name
            == "atlas_query_asset_status"
        ):

            # ------------------------------------------------------
            # The semantic plan is authoritative.
            #
            # Qwen may decide that status evidence is needed, but it
            # cannot broaden or alter the canonical inventory query.
            # ------------------------------------------------------

            planned_args = {
                "status":
                    plan.status_filter,

                "asset_type":
                    plan.asset_type,

                "criticality":
                    plan.criticality,

                "role":
                    plan.role,
            }

        if (
            planned_args
            != tool_args
        ):

            print(
                "[ATLAS TOOL POLICY]",
                name,
                json.dumps(
                    planned_args,
                    ensure_ascii=False,
                    default=str,
                ),
                flush=True,
            )

        result = await verified_tool_call(
            ctx,
            call_tool,
            name,
            planned_args,
        )

        # ----------------------------------------------------------
        # Partition freshly exposed verified facts through the fixed
        # deterministic investigation scope BEFORE another model
        # turn is allowed to use them.
        #
        # The EvidenceLedger retains all verified facts for audit.
        # Only accepted FACT ids are exposed as admissible evidence.
        # ----------------------------------------------------------

        raw_result = structured_tool_result(
            result
        )

        candidate_fact_ids = (
            raw_result.get(
                "verified_fact_ids",
                [],
            )
            if isinstance(
                raw_result,
                dict,
            )
            else []
        )

        candidate_fact_ids = [
            str(
                fact_id
            )
            for fact_id
            in candidate_fact_ids
            if str(
                fact_id
            ).strip()
        ]

        if candidate_fact_ids:

            scoped = validate_fact_selection(
                scope,
                ctx.deps,
                candidate_fact_ids,
            )

            print(
                "\n[ATLAS IN-SCOPE FACTS]",
                scoped.accepted_fact_ids,
                flush=True,
            )

            if scoped.rejected_fact_ids:

                rejected = {
                    fact_id:
                        scoped.reasons.get(
                            fact_id
                        )
                    for fact_id
                    in scoped.rejected_fact_ids
                }

                print(
                    "[SCOPE REJECT]",
                    rejected,
                    flush=True,
                )

            # ------------------------------------------------------
            # Keep raw facts in the ledger, but do not advertise
            # rejected FACT ids to the investigator as selectable
            # evidence.
            # ------------------------------------------------------

            if isinstance(
                result,
                dict,
            ):

                result = dict(
                    result
                )

                result[
                    "verified_fact_ids"
                ] = list(
                    scoped.accepted_fact_ids
                )

            # ------------------------------------------------------
            # Deterministic terminal condition:
            #
            # The tool successfully produced verified facts, but
            # ATLAS already proved that every one is irrelevant to
            # the fixed scope. Another LLM turn cannot make those
            # facts relevant.
            # ------------------------------------------------------

            if (
                not scoped.accepted_fact_ids
                and scoped.rejected_fact_ids
            ):

                raise NoInScopeEvidenceError(
                    {
                        fact_id:
                            scoped.reasons.get(
                                fact_id,
                                "OUT_OF_SCOPE",
                            )
                        for fact_id
                        in scoped.rejected_fact_ids
                    }
                )

        return result

    atlas_knowledge = (
        MCPToolset(
            transport,
            process_tool_call=(
                planned_verified_tool_call
            ),
        )
        .filtered(
            lambda ctx, tool_def:
                tool_def.name
                in allowed_tools
        )
    )

    agent = Agent(
        model=model,
        deps_type=EvidenceLedger,
        output_type=InvestigationReport,
        instructions=build_investigator_instructions(
            plan,
            scope,
            resolved_reference,
        ),
        toolsets=[
            atlas_knowledge,
        ],
        model_settings=ModelSettings(
            max_tokens=4096,
            temperature=0.0,
        ),
        retries=2,
    )

    register_output_validator(
        agent,
        scope,
    )

    try:

        result = await agent.run(
            question,
            deps=ledger,
            usage_limits=UsageLimits(
                request_limit=6,
                tool_calls_limit=5,
            ),
        )

    except NoInScopeEvidenceError as exc:

        print()
        print(
            "[NO IN-SCOPE EVIDENCE]",
            exc.reasons,
            flush=True,
        )

        report = InvestigationReport(
            status="INSUFFICIENT_EVIDENCE",
            fact_ids=[],
        )

        print_report(
            report,
            ledger,
        )

        return

    except UsageLimitExceeded as exc:

        print()
        print(
            "[INVESTIGATION BUDGET EXHAUSTED]",
            str(exc),
        )

        report = InvestigationReport(
            status="INSUFFICIENT_EVIDENCE",
            fact_ids=[],
        )

        print_report(
            report,
            ledger,
        )

        return

    report = result.output

    print_report(
        report,
        ledger,
    )

    print()
    print("=" * 80)
    print("INVESTIGATION USAGE")
    print("=" * 80)

    print(
        result.usage
    )


# =============================================================================
# CLI
# =============================================================================

def main() -> None:

    validate_configuration()

    question = " ".join(
        sys.argv[1:]
    ).strip()

    if not question:

        raise SystemExit(
            'Usage: investigator_verified_smoke.py "question"'
        )

    asyncio.run(
        investigate(
            question
        )
    )


if __name__ == "__main__":
    main()
