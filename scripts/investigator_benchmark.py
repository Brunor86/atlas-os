#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SMOKE_SCRIPT = (
    ROOT
    / "scripts"
    / "investigator_verified_smoke.py"
)


# =============================================================================
# CONTRACT
# =============================================================================


@dataclass(frozen=True)
class BenchmarkCase:

    case_id: str

    title: str

    question: str

    expected_plan: dict[str, Any]

    expected_status: str

    expected_tool_scope: set[str] | None = None

    expected_tools: list[str] | None = None

    expected_tool_arguments: dict[
        str,
        dict[str, Any],
    ] = field(
        default_factory=dict
    )

    expected_preflight_status: str | None = None

    forbidden_tools: set[str] = field(
        default_factory=set
    )

    required_plan_fields: set[str] = field(
        default_factory=set
    )

    require_unsupported_domain: bool = False


CASES = [

    BenchmarkCase(
        case_id="01",
        title="GROUP RELATION",
        question="¿De qué depende Immich?",
        expected_plan={
            "domain": "RELATION",
            "scope_mode": "TARGET",
            "relationship": "DEPENDS_ON",
            "relation_anchor": "SUBJECT",
            "direction": "DOWNSTREAM",
            "global_scope": False,
        },
        expected_status="ANSWERED",
        expected_tool_scope={
            "atlas_query_entity_relations",
        },
        expected_tools=[
            "atlas_query_entity_relations",
        ],
        expected_tool_arguments={
            "atlas_query_entity_relations": {
                "relationship": "DEPENDS_ON",
                "direction": "downstream",
            },
        },
        expected_preflight_status="SUCCESS",
    ),

    BenchmarkCase(
        case_id="02",
        title="REVERSE RELATION",
        question="¿Qué depende de immich_postgres?",
        expected_plan={
            "domain": "RELATION",
            "scope_mode": "TARGET",
            "relationship": "DEPENDS_ON",
            "relation_anchor": "OBJECT",
            "direction": "UPSTREAM",
            "global_scope": False,
        },
        expected_status="ANSWERED",
        expected_tool_scope={
            "atlas_query_entity_relations",
        },
        expected_tools=[
            "atlas_query_entity_relations",
        ],
        expected_tool_arguments={
            "atlas_query_entity_relations": {
                "relationship": "DEPENDS_ON",
                "direction": "upstream",
            },
        },
        expected_preflight_status="SUCCESS",
    ),

    BenchmarkCase(
        case_id="03",
        title="ATTENTION",
        question="¿Qué necesita atención en mi infraestructura?",
        expected_plan={
            "domain": "ATTENTION",
            "scope_mode": "GLOBAL",
            "global_scope": True,
        },
        expected_status="ANSWERED",
        expected_tool_scope={
            "atlas_attention_summary",
        },
        expected_tools=[
            "atlas_attention_summary",
        ],
    ),

    BenchmarkCase(
        case_id="04",
        title="UNKNOWN ENTITY",
        question="¿De qué depende un-servicio-que-no-existe?",
        expected_plan={
            "domain": "RELATION",
            "scope_mode": "TARGET",
            "relationship": "DEPENDS_ON",
            "relation_anchor": "SUBJECT",
            "direction": "DOWNSTREAM",
            "global_scope": False,
        },
        expected_status="INSUFFICIENT_EVIDENCE",
        expected_tools=[],
        expected_preflight_status="NOT_FOUND",
    ),

    BenchmarkCase(
        case_id="05",
        title="VERIFIED STATUS COLLECTION",
        question="¿Qué aplicaciones están offline?",
        expected_plan={
            "domain": "STATUS",
            "scope_mode": "COLLECTION",
            "asset_type": "APPLICATION",
            "status_filter": "OFFLINE",
            "global_scope": False,
        },
        required_plan_fields={
            "collection_query",
        },
        expected_status="ANSWERED",
        expected_tool_scope={
            "atlas_query_asset_status",
        },
        expected_tools=[
            "atlas_query_asset_status",
        ],
        expected_tool_arguments={
            "atlas_query_asset_status": {
                "status": "OFFLINE",
                "asset_type": "APPLICATION",
                "criticality": None,
                "role": None,
            },
        },
        forbidden_tools={
            "atlas_semantic_query",
            "atlas_search_assets",
            "atlas_describe_asset",
            "atlas_resolve_entity",
            "atlas_query_entity_relations",
            "atlas_query_relations",
            "atlas_attention_summary",
        },
    ),

    BenchmarkCase(
        case_id="06",
        title="UNSUPPORTED OBSERVATION",
        question="¿Qué temperatura tiene el disco?",
        expected_plan={
            "domain": "OBSERVATION",
            "scope_mode": "TARGET",
            "global_scope": False,
        },
        required_plan_fields={
            "target_query",
            "observation",
        },
        expected_status="INSUFFICIENT_EVIDENCE",
        expected_tools=[],
    ),

    BenchmarkCase(
        case_id="07",
        title="HEALTH RELEVANCE TRAP",
        question="¿Tiene algún problema Immich?",
        expected_plan={
            "domain": "HEALTH",
            "scope_mode": "TARGET",
            "global_scope": False,
        },
        expected_status="INSUFFICIENT_EVIDENCE",
        expected_tool_scope={
            "atlas_attention_summary",
        },
        expected_tools=[
            "atlas_attention_summary",
        ],
        expected_preflight_status="SUCCESS",
        forbidden_tools={
            "atlas_semantic_query",
            "atlas_search_assets",
            "atlas_describe_asset",
            "atlas_query_entity_relations",
        },
    ),
]


# =============================================================================
# PARSING
# =============================================================================


def extract_json_block(
    text: str,
    title: str,
) -> dict[str, Any] | None:

    pattern = (
        rf"{re.escape(title)}"
        rf"\n=+\n"
        rf"(\{{.*?\n\}})"
    )

    match = re.search(
        pattern,
        text,
        re.DOTALL,
    )

    if not match:

        return None

    try:

        return json.loads(
            match.group(1)
        )

    except json.JSONDecodeError:

        return None


def extract_tool_scope(
    text: str,
) -> set[str] | None:

    match = re.search(
        r"^\[TOOL SCOPE\]\s+(.+)$",
        text,
        re.MULTILINE,
    )

    if not match:

        return None

    try:

        value = ast.literal_eval(
            match.group(1)
        )

    except Exception:

        return None

    return set(value)


def extract_tool_calls(
    text: str,
) -> list[
    tuple[
        str,
        dict[str, Any],
    ]
]:

    calls = []

    pattern = re.compile(
        r"^\[ATLAS TOOL\]\s+"
        r"([^\s]+)"
        r"(?:\s+(\{.*\}))?$",
        re.MULTILINE,
    )

    for match in pattern.finditer(
        text
    ):

        name = match.group(1)

        raw_arguments = (
            match.group(2)
            or "{}"
        )

        try:

            arguments = json.loads(
                raw_arguments
            )

        except json.JSONDecodeError:

            arguments = {}

        calls.append(
            (
                name,
                arguments,
            )
        )

    return calls


def extract_preflight_status(
    text: str,
) -> str | None:

    match = re.search(
        r"^\[ATLAS PREFLIGHT STATUS\]\s+(.+)$",
        text,
        re.MULTILINE,
    )

    if not match:

        return None

    return (
        match
        .group(1)
        .strip()
    )


def extract_usage(
    text: str,
) -> dict[str, int]:

    matches = re.findall(
        r"RunUsage\("
        r"input_tokens=(\d+), "
        r"output_tokens=(\d+), "
        r"requests=(\d+)"
        r"(?:, tool_calls=(\d+))?"
        r"\)",
        text,
    )

    if not matches:

        return {}

    input_tokens = 0
    output_tokens = 0
    requests = 0
    tool_calls = 0

    for match in matches:

        input_tokens += int(
            match[0]
        )

        output_tokens += int(
            match[1]
        )

        requests += int(
            match[2]
        )

        if match[3]:

            tool_calls += int(
                match[3]
            )

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "requests": requests,
        "tool_calls": tool_calls,
    }


# =============================================================================
# VALIDATION
# =============================================================================


def validate_case(
    case: BenchmarkCase,
    output: str,
) -> tuple[
    list[str],
    dict[str, Any],
]:

    failures = []

    plan = extract_json_block(
        output,
        "INVESTIGATION PLAN",
    )

    report = extract_json_block(
        output,
        "STRUCTURED REPORT",
    )

    tool_scope = extract_tool_scope(
        output
    )

    tool_calls = extract_tool_calls(
        output
    )

    tool_names = [
        name
        for name, _
        in tool_calls
    ]

    preflight_status = (
        extract_preflight_status(
            output
        )
    )

    usage = extract_usage(
        output
    )


    # -------------------------------------------------------------------------
    # PLAN
    # -------------------------------------------------------------------------

    if plan is None:

        failures.append(
            "missing INVESTIGATION PLAN"
        )

    else:

        for key, expected in (
            case.expected_plan.items()
        ):

            actual = plan.get(
                key
            )

            if actual != expected:

                failures.append(
                    "plan."
                    f"{key}: "
                    f"expected={expected!r} "
                    f"actual={actual!r}"
                )


    if plan is not None:

        for field_name in (
            case.required_plan_fields
        ):

            value = plan.get(
                field_name
            )

            if (
                value is None
                or (
                    isinstance(
                        value,
                        str,
                    )
                    and not value.strip()
                )
            ):

                failures.append(
                    "plan."
                    f"{field_name}: "
                    "required semantic field missing"
                )


    # -------------------------------------------------------------------------
    # REPORT
    # -------------------------------------------------------------------------

    if report is None:

        failures.append(
            "missing STRUCTURED REPORT"
        )

    else:

        actual_status = report.get(
            "status"
        )

        if (
            actual_status
            != case.expected_status
        ):

            failures.append(
                "status: "
                f"expected={case.expected_status!r} "
                f"actual={actual_status!r}"
            )


    # -------------------------------------------------------------------------
    # TOOL SCOPE
    # -------------------------------------------------------------------------

    if (
        case.expected_tool_scope
        is not None
    ):

        if (
            tool_scope
            != case.expected_tool_scope
        ):

            failures.append(
                "tool_scope: "
                f"expected="
                f"{sorted(case.expected_tool_scope)!r} "
                f"actual="
                f"{sorted(tool_scope) if tool_scope is not None else None!r}"
            )


    # -------------------------------------------------------------------------
    # TOOL CALLS
    # -------------------------------------------------------------------------

    if (
        case.expected_tools
        is not None
    ):

        if (
            tool_names
            != case.expected_tools
        ):

            failures.append(
                "tools: "
                f"expected={case.expected_tools!r} "
                f"actual={tool_names!r}"
            )


    for forbidden in (
        case.forbidden_tools
    ):

        if forbidden in tool_names:

            failures.append(
                "forbidden tool used: "
                f"{forbidden}"
            )


    # -------------------------------------------------------------------------
    # TOOL ARGUMENTS
    # -------------------------------------------------------------------------

    calls_by_name = {
        name: arguments
        for name, arguments
        in tool_calls
    }

    for (
        tool_name,
        expected_arguments,
    ) in (
        case
        .expected_tool_arguments
        .items()
    ):

        actual_arguments = (
            calls_by_name.get(
                tool_name
            )
        )

        if actual_arguments is None:

            failures.append(
                "tool arguments missing: "
                f"{tool_name}"
            )

            continue

        for (
            argument,
            expected_value,
        ) in (
            expected_arguments.items()
        ):

            actual_value = (
                actual_arguments.get(
                    argument
                )
            )

            if (
                actual_value
                != expected_value
            ):

                failures.append(
                    f"{tool_name}."
                    f"{argument}: "
                    f"expected="
                    f"{expected_value!r} "
                    f"actual="
                    f"{actual_value!r}"
                )


    # -------------------------------------------------------------------------
    # PREFLIGHT
    # -------------------------------------------------------------------------

    if (
        case.expected_preflight_status
        is not None
    ):

        if (
            preflight_status
            != case.expected_preflight_status
        ):

            failures.append(
                "preflight: "
                f"expected="
                f"{case.expected_preflight_status!r} "
                f"actual="
                f"{preflight_status!r}"
            )


    # -------------------------------------------------------------------------
    # UNSUPPORTED DOMAIN
    # -------------------------------------------------------------------------

    if (
        case.require_unsupported_domain
        and (
            "[UNSUPPORTED EVIDENCE DOMAIN]"
            not in output
        )
    ):

        failures.append(
            "missing unsupported-domain "
            "fail-closed marker"
        )


    details = {
        "plan": plan,
        "report": report,
        "tool_scope": (
            sorted(tool_scope)
            if tool_scope is not None
            else None
        ),
        "tools": tool_names,
        "preflight": preflight_status,
        "usage": usage,
        "scope_reject": (
            "[SCOPE REJECT]"
            in output
        ),
    }

    return (
        failures,
        details,
    )


# =============================================================================
# EXECUTION
# =============================================================================


def run_case(
    case: BenchmarkCase,
    timeout: int,
    show_output: bool,
) -> bool:

    command = [
        sys.executable,
        str(
            SMOKE_SCRIPT
        ),
        case.question,
    ]

    try:

        process = subprocess.run(
            command,
            cwd=ROOT,
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )

    except subprocess.TimeoutExpired as exc:

        output = (
            exc.stdout
            or ""
        )

        if isinstance(
            output,
            bytes,
        ):

            output = output.decode(
                errors="replace"
            )

        log_path = (
            Path(
                tempfile.gettempdir()
            )
            / (
                "atlas-investigator-"
                f"benchmark-{case.case_id}.log"
            )
        )

        log_path.write_text(
            output
        )

        print(
            f"FAIL {case.case_id} "
            f"{case.title}"
        )

        print(
            f"     timeout after "
            f"{timeout}s"
        )

        print(
            "     "
            f"log={log_path}"
        )

        return False


    output = (
        process.stdout
        or ""
    )


    if show_output:

        print(output)


    failures, details = (
        validate_case(
            case,
            output,
        )
    )


    passed = (
        process.returncode == 0
        and not failures
    )


    status = (
        "PASS"
        if passed
        else "FAIL"
    )


    print(
        f"{status} "
        f"{case.case_id} "
        f"{case.title}"
    )

    plan = (
        details.get(
            "plan"
        )
        or {}
    )

    report = (
        details.get(
            "report"
        )
        or {}
    )

    usage = (
        details.get(
            "usage"
        )
        or {}
    )

    print(
        "     "
        f"plan="
        f"{plan.get('domain')} "
        f"status="
        f"{report.get('status')} "
        f"tools="
        f"{details.get('tools')}"
    )

    if usage:

        print(
            "     "
            f"tokens="
            f"{usage.get('input_tokens', 0)}+"
            f"{usage.get('output_tokens', 0)} "
            f"requests="
            f"{usage.get('requests', 0)} "
            f"tool_calls="
            f"{usage.get('tool_calls', 0)}"
        )

    if details.get(
        "scope_reject"
    ):

        print(
            "     "
            "scope_reject=yes"
        )


    if failures:

        for failure in failures:

            print(
                "     "
                f"- {failure}"
            )


    if process.returncode != 0:

        print(
            "     "
            f"- process exit code "
            f"{process.returncode}"
        )


    if not passed:

        log_path = (
            Path(
                tempfile.gettempdir()
            )
            / (
                "atlas-investigator-"
                f"benchmark-{case.case_id}.log"
            )
        )

        log_path.write_text(
            output
        )

        print(
            "     "
            f"log={log_path}"
        )


    return passed


# =============================================================================
# CLI
# =============================================================================


def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "ATLAS live Investigator "
            "intelligence benchmark"
        )
    )

    parser.add_argument(
        "--case",
        action="append",
        dest="case_ids",
        help=(
            "Run only one benchmark case. "
            "May be repeated."
        ),
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=240,
        help=(
            "Per-case timeout in seconds "
            "(default: 240)."
        ),
    )

    parser.add_argument(
        "--show-output",
        action="store_true",
        help=(
            "Print complete Investigator output."
        ),
    )

    args = parser.parse_args()


    selected = CASES

    if args.case_ids:

        wanted = set(
            args.case_ids
        )

        selected = [
            case
            for case in CASES
            if case.case_id in wanted
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


    print(
        "=" * 80
    )

    print(
        "ATLAS INTELLIGENCE BENCHMARK"
    )

    print(
        "=" * 80
    )

    print(
        f"Python: {sys.executable}"
    )

    print(
        f"Cases: {len(selected)}"
    )

    print()


    passed = 0

    failed = 0


    for case in selected:

        ok = run_case(
            case,
            timeout=args.timeout,
            show_output=args.show_output,
        )

        if ok:

            passed += 1

        else:

            failed += 1

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
        f"PASS: {passed}"
    )

    print(
        f"FAIL: {failed}"
    )

    print(
        f"TOTAL: {passed + failed}"
    )


    return (
        0
        if failed == 0
        else 1
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
