#!/usr/bin/env python3

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import sys

from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SMOKE_PATH = (
    ROOT
    / "scripts"
    / "investigator_verified_smoke.py"
)


# =============================================================================
# LOAD REAL PLANNER ADAPTER
# =============================================================================


def load_smoke_module():

    spec = importlib.util.spec_from_file_location(
        "atlas_investigator_verified_smoke",
        SMOKE_PATH,
    )

    if (
        spec is None
        or spec.loader is None
    ):

        raise RuntimeError(
            "Unable to load investigator smoke adapter."
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[
        spec.name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


smoke = load_smoke_module()


# =============================================================================
# BENCHMARK CONTRACT
# =============================================================================


@dataclass(frozen=True)
class PlannerCase:

    case_id: str

    title: str

    question: str

    domain: str

    scope_mode: str

    relationship: str | None = None

    relation_anchor: str | None = None

    direction: str | None = None

    asset_type: str | None = None

    role: str | None = None

    criticality: str | None = None

    status_filter: str | None = None

    require_target: bool = False

    require_collection: bool = False

    require_observation: bool = False


CASES = [

    PlannerCase(
        case_id="01",
        title="GROUP RELATION",
        question="¿De qué depende Immich?",
        domain="RELATION",
        scope_mode="TARGET",
        relationship="DEPENDS_ON",
        relation_anchor="SUBJECT",
        direction="DOWNSTREAM",
        require_target=True,
    ),

    PlannerCase(
        case_id="02",
        title="REVERSE RELATION",
        question="¿Qué depende de immich_postgres?",
        domain="RELATION",
        scope_mode="TARGET",
        relationship="DEPENDS_ON",
        relation_anchor="OBJECT",
        direction="UPSTREAM",
        require_target=True,
    ),

    PlannerCase(
        case_id="03",
        title="GLOBAL ATTENTION",
        question="¿Qué necesita atención en mi infraestructura?",
        domain="ATTENTION",
        scope_mode="GLOBAL",
    ),

    PlannerCase(
        case_id="04",
        title="UNKNOWN ENTITY RELATION",
        question="¿De qué depende un-servicio-que-no-existe?",
        domain="RELATION",
        scope_mode="TARGET",
        relationship="DEPENDS_ON",
        relation_anchor="SUBJECT",
        direction="DOWNSTREAM",
        require_target=True,
    ),

    PlannerCase(
        case_id="05",
        title="APPLICATION STATUS COLLECTION",
        question="¿Qué aplicaciones están offline?",
        domain="STATUS",
        scope_mode="COLLECTION",
        asset_type="APPLICATION",
        status_filter="OFFLINE",
        require_collection=True,
    ),

    PlannerCase(
        case_id="06",
        title="TARGETED OBSERVATION",
        question="¿Qué temperatura tiene el disco?",
        domain="OBSERVATION",
        scope_mode="TARGET",
        require_target=True,
        require_observation=True,
    ),

    PlannerCase(
        case_id="07",
        title="TARGETED HEALTH",
        question="¿Tiene algún problema Immich?",
        domain="HEALTH",
        scope_mode="TARGET",
        require_target=True,
    ),
]


# =============================================================================
# HELPERS
# =============================================================================


def enum_value(
    value: Any,
):

    if value is None:

        return None

    return getattr(
        value,
        "value",
        value,
    )


def non_empty(
    value: Any,
) -> bool:

    return (
        isinstance(
            value,
            str,
        )
        and bool(
            value.strip()
        )
    )


def validate_plan(
    case: PlannerCase,
    plan,
) -> list[str]:

    failures = []


    actual_domain = enum_value(
        plan.domain
    )

    actual_scope_mode = enum_value(
        plan.scope_mode
    )

    actual_anchor = enum_value(
        plan.relation_anchor
    )

    actual_direction = enum_value(
        plan.direction
    )


    if (
        actual_domain
        != case.domain
    ):

        failures.append(
            "domain "
            f"expected={case.domain} "
            f"actual={actual_domain}"
        )


    if (
        actual_scope_mode
        != case.scope_mode
    ):

        failures.append(
            "scope_mode "
            f"expected={case.scope_mode} "
            f"actual={actual_scope_mode}"
        )


    if (
        case.relationship
        is not None
        and plan.relationship
        != case.relationship
    ):

        failures.append(
            "relationship "
            f"expected={case.relationship} "
            f"actual={plan.relationship}"
        )


    if (
        case.relation_anchor
        is not None
        and actual_anchor
        != case.relation_anchor
    ):

        failures.append(
            "relation_anchor "
            f"expected={case.relation_anchor} "
            f"actual={actual_anchor}"
        )


    if (
        case.direction
        is not None
        and actual_direction
        != case.direction
    ):

        failures.append(
            "direction "
            f"expected={case.direction} "
            f"actual={actual_direction}"
        )


    for (
        field_name,
        expected_value,
    ) in (
        (
            "asset_type",
            case.asset_type,
        ),
        (
            "role",
            case.role,
        ),
        (
            "criticality",
            case.criticality,
        ),
        (
            "status_filter",
            case.status_filter,
        ),
    ):

        if (
            expected_value
            is not None
            and getattr(
                plan,
                field_name,
            )
            != expected_value
        ):

            failures.append(
                f"{field_name} "
                f"expected={expected_value} "
                f"actual={getattr(plan, field_name)}"
            )


    if (
        case.require_target
        and not non_empty(
            plan.target_query
        )
    ):

        failures.append(
            "target_query missing"
        )


    if (
        case.require_collection
        and not non_empty(
            plan.collection_query
        )
    ):

        failures.append(
            "collection_query missing"
        )


    if (
        case.require_observation
        and not non_empty(
            plan.observation
        )
    ):

        failures.append(
            "observation missing"
        )


    return failures


# =============================================================================
# EXECUTION
# =============================================================================


async def run_trial(
    case: PlannerCase,
    trial: int,
    model,
):

    try:

        plan, usage = (
            await smoke.create_investigation_plan(
                case.question,
                model,
            )
        )

    except Exception as exc:

        return {
            "case": case,
            "trial": trial,
            "plan": None,
            "usage": None,
            "failures": [
                "planner exception: "
                f"{type(exc).__name__}: {exc}"
            ],
        }


    failures = validate_plan(
        case,
        plan,
    )


    return {
        "case": case,
        "trial": trial,
        "plan": plan,
        "usage": usage,
        "failures": failures,
    }


async def main_async(
    selected: list[PlannerCase],
    trials: int,
):

    model = smoke.OllamaModel(
        smoke.MODEL_NAME,
        provider=smoke.OllamaProvider(
            base_url=smoke.OLLAMA_BASE_URL,
        ),
    )


    print(
        "=" * 80
    )

    print(
        "ATLAS PLANNER RELIABILITY BENCHMARK"
    )

    print(
        "=" * 80
    )

    print(
        "MODEL:",
        smoke.MODEL_NAME,
    )

    print(
        "CASES:",
        len(selected),
    )

    print(
        "TRIALS PER CASE:",
        trials,
    )

    print()


    total_runs = 0

    exact_passes = 0

    field_totals = {
        "domain": 0,
        "scope_mode": 0,
        "relationship": 0,
        "relation_anchor": 0,
        "direction": 0,
        "target_query": 0,
        "collection_query": 0,
        "observation": 0,
        "asset_type": 0,
        "role": 0,
        "criticality": 0,
        "status_filter": 0,
    }

    field_possible = {
        key: 0
        for key in field_totals
    }


    for case in selected:

        case_passes = 0

        print(
            "=" * 80
        )

        print(
            f"{case.case_id} {case.title}"
        )

        print(
            "QUESTION:",
            case.question,
        )

        print(
            "=" * 80
        )


        for trial in range(
            1,
            trials + 1,
        ):

            result = await run_trial(
                case,
                trial,
                model,
            )

            total_runs += 1

            plan = result[
                "plan"
            ]

            failures = result[
                "failures"
            ]


            if plan is None:

                print(
                    f"FAIL trial={trial}"
                )

                for failure in failures:

                    print(
                        "     -",
                        failure,
                    )

                continue


            actual = {
                "domain":
                    enum_value(
                        plan.domain
                    ),

                "scope_mode":
                    enum_value(
                        plan.scope_mode
                    ),

                "relationship":
                    plan.relationship,

                "relation_anchor":
                    enum_value(
                        plan.relation_anchor
                    ),

                "direction":
                    enum_value(
                        plan.direction
                    ),

                "target_query":
                    plan.target_query,

                "collection_query":
                    plan.collection_query,

                "observation":
                    plan.observation,

                "asset_type":
                    plan.asset_type,

                "role":
                    plan.role,

                "criticality":
                    plan.criticality,

                "status_filter":
                    plan.status_filter,
            }


            expected_checks = {
                "domain":
                    case.domain,

                "scope_mode":
                    case.scope_mode,
            }


            if (
                case.relationship
                is not None
            ):

                expected_checks[
                    "relationship"
                ] = (
                    case.relationship
                )


            if (
                case.relation_anchor
                is not None
            ):

                expected_checks[
                    "relation_anchor"
                ] = (
                    case.relation_anchor
                )


            if (
                case.direction
                is not None
            ):

                expected_checks[
                    "direction"
                ] = (
                    case.direction
                )


            for (
                field_name,
                expected_value,
            ) in expected_checks.items():

                field_possible[
                    field_name
                ] += 1

                if (
                    actual[
                        field_name
                    ]
                    == expected_value
                ):

                    field_totals[
                        field_name
                    ] += 1


            for (
                field_name,
                expected_value,
            ) in (
                (
                    "asset_type",
                    case.asset_type,
                ),
                (
                    "role",
                    case.role,
                ),
                (
                    "criticality",
                    case.criticality,
                ),
                (
                    "status_filter",
                    case.status_filter,
                ),
            ):

                if expected_value is None:
                    continue

                field_possible[
                    field_name
                ] += 1

                if (
                    actual[
                        field_name
                    ]
                    == expected_value
                ):

                    field_totals[
                        field_name
                    ] += 1


            if case.require_target:

                field_possible[
                    "target_query"
                ] += 1

                if non_empty(
                    plan.target_query
                ):

                    field_totals[
                        "target_query"
                    ] += 1


            if case.require_collection:

                field_possible[
                    "collection_query"
                ] += 1

                if non_empty(
                    plan.collection_query
                ):

                    field_totals[
                        "collection_query"
                    ] += 1


            if case.require_observation:

                field_possible[
                    "observation"
                ] += 1

                if non_empty(
                    plan.observation
                ):

                    field_totals[
                        "observation"
                    ] += 1


            if not failures:

                exact_passes += 1
                case_passes += 1

                print(
                    f"PASS trial={trial} "
                    f"scope={actual['scope_mode']}"
                )

            else:

                print(
                    f"FAIL trial={trial} "
                    f"scope={actual['scope_mode']}"
                )

                print(
                    "     plan=",
                    plan.model_dump_json(),
                )

                for failure in failures:

                    print(
                        "     -",
                        failure,
                    )


        print()

        print(
            "CASE ACCURACY:",
            f"{case_passes}/{trials}",
            (
                f"({case_passes / trials * 100:.1f}%)"
            ),
        )

        print()


    print(
        "=" * 80
    )

    print(
        "SUMMARY"
    )

    print(
        "=" * 80
    )

    print(
        "EXACT PLANS:",
        f"{exact_passes}/{total_runs}",
        (
            f"({exact_passes / total_runs * 100:.1f}%)"
            if total_runs
            else "(n/a)"
        ),
    )

    print()


    print(
        "FIELD ACCURACY"
    )

    for field_name in (
        field_totals
    ):

        possible = (
            field_possible[
                field_name
            ]
        )

        if not possible:

            continue

        correct = (
            field_totals[
                field_name
            ]
        )

        print(
            f"{field_name:18s}",
            f"{correct}/{possible}",
            (
                f"({correct / possible * 100:.1f}%)"
            ),
        )


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Measure repeated semantic planning "
            "reliability without MCP investigation."
        )
    )

    parser.add_argument(
        "--case",
        action="append",
        dest="case_ids",
    )

    parser.add_argument(
        "--trials",
        type=int,
        default=5,
    )

    args = parser.parse_args()


    if args.trials < 1:

        parser.error(
            "--trials must be >= 1"
        )


    selected = CASES

    if args.case_ids:

        wanted = set(
            args.case_ids
        )

        selected = [
            case
            for case in CASES
            if case.case_id
            in wanted
        ]

        missing = (
            wanted
            - {
                case.case_id
                for case in selected
            }
        )

        if missing:

            parser.error(
                "unknown cases: "
                + ", ".join(
                    sorted(
                        missing
                    )
                )
            )


    asyncio.run(
        main_async(
            selected,
            args.trials,
        )
    )


if __name__ == "__main__":

    main()
