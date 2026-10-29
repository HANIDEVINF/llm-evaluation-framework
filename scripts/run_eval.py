#!/usr/bin/env python3
"""Run deterministic smoke checks against candidate responses.

This script does not call an LLM, calculate a latency/cost benchmark, or claim
that the illustrative fixtures represent a real model evaluation.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def load_suite(path: Path) -> dict[str, Any]:
    suite = load_json(path)
    cases = suite.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Benchmark suite must contain a non-empty 'cases' array.")
    if suite.get("total_cases") != len(cases):
        raise ValueError(
            f"total_cases says {suite.get('total_cases')!r}, but the suite contains {len(cases)} cases."
        )
    ids = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(ids) != len(cases) or any(not isinstance(case_id, str) or not case_id for case_id in ids):
        raise ValueError("Every benchmark case must be an object with a non-empty string id.")
    if len(set(ids)) != len(ids):
        raise ValueError("Benchmark case ids must be unique.")
    return suite


def load_responses(path: Path) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"Cannot read response JSONL {path}: {exc}") from exc

    for line_no, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on {path}:{line_no}: {exc}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"Each JSONL record on {path}:{line_no} must be an object.")
        case_id = record.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"Each record on {path}:{line_no} needs a string case_id.")
        if case_id in results:
            raise ValueError(f"Duplicate response for case_id {case_id!r}.")
        response = record.get("response", "")
        if not isinstance(response, str):
            raise ValueError(f"'response' for {case_id!r} must be a string.")
        results[case_id] = record
    if not results:
        raise ValueError("Response file has no JSONL records.")
    return results


def evaluate_case(case: dict[str, Any], record: dict[str, Any] | None) -> dict[str, Any]:
    """Evaluate one response using transparent deterministic assertions."""
    failures: list[str] = []
    if record is None:
        return {
            "case_id": case["id"],
            "category": case.get("category", "uncategorized"),
            "passed": False,
            "checks": [],
            "failures": ["No candidate response supplied."],
        }

    text = str(record.get("response", "")).casefold()
    checks: list[dict[str, Any]] = []

    for alternatives in case.get("required_any", []):
        matched = [term for term in alternatives if str(term).casefold() in text]
        passed = bool(matched)
        checks.append({"kind": "required_any", "passed": passed, "matched": matched})
        if not passed:
            failures.append(f"None of the required alternatives were found: {alternatives}")

    for term in case.get("prohibited_terms", []):
        found = str(term).casefold() in text
        checks.append({"kind": "prohibited_term", "term": term, "passed": not found})
        if found:
            failures.append(f"Prohibited phrase found: {term}")

    for term in case.get("must_not_contain", []):
        found = str(term).casefold() in text
        checks.append({"kind": "privacy_absence", "term": term, "passed": not found})
        if found:
            failures.append(f"Synthetic sensitive fixture value was reproduced: {term}")

    if "expected_tool_call" in case:
        actual = record.get("tool_call")
        passed = actual == case["expected_tool_call"]
        checks.append({"kind": "exact_tool_call", "passed": passed})
        if not passed:
            failures.append("tool_call did not exactly match expected_tool_call.")

    return {
        "case_id": case["id"],
        "category": case.get("category", "uncategorized"),
        "passed": not failures,
        "checks": checks,
        "failures": failures,
    }


def evaluate_suite(suite: dict[str, Any], responses: dict[str, dict[str, Any]], config: str) -> dict[str, Any]:
    cases = suite["cases"]
    known_ids = {case["id"] for case in cases}
    unexpected_ids = sorted(set(responses) - known_ids)
    if unexpected_ids:
        raise ValueError(f"Responses contain unknown case ids: {unexpected_ids}")

    case_results = [evaluate_case(case, responses.get(case["id"])) for case in cases]
    by_category: dict[str, dict[str, int | float]] = {}
    for result in case_results:
        category = result["category"]
        bucket = by_category.setdefault(category, {"passed": 0, "total": 0})
        bucket["total"] += 1
        bucket["passed"] += int(result["passed"])
    for bucket in by_category.values():
        bucket["pass_rate"] = bucket["passed"] / bucket["total"] if bucket["total"] else 0.0

    passed_count = sum(int(result["passed"]) for result in case_results)
    return {
        "report_version": 1,
        "status": "PASS" if passed_count == len(cases) else "FAIL",
        "config": config,
        "suite": suite.get("dataset_name", "unnamed-suite"),
        "suite_version": suite.get("version"),
        "evaluation_mode": "deterministic_smoke_checks",
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_cases": len(cases),
        "passed_cases": passed_count,
        "failed_cases": len(cases) - passed_count,
        "pass_rate": passed_count / len(cases),
        "limitations": suite.get("limitations", []),
        "measurement_note": (
            "Checks were computed from the supplied response JSONL. This runner does not call a model "
            "and does not measure latency, token cost, calibration, or broad model quality."
        ),
        "categories": by_category,
        "results": case_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="EvalGate deterministic response smoke-check runner")
    parser.add_argument("--suite", type=Path, default=ROOT / "benchmarks" / "benchmark_suite_v1.json")
    parser.add_argument(
        "--responses",
        type=Path,
        required=True,
        help="JSONL of candidate outputs; one object per case with case_id and response, plus tool_call when applicable.",
    )
    parser.add_argument(
        "--config",
        default="candidate-not-specified",
        help="Human-readable candidate/configuration label; this does not select or call a model.",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "latest_regression_report.json")
    args = parser.parse_args()

    try:
        suite = load_suite(args.suite)
        responses = load_responses(args.responses)
        report = evaluate_suite(suite, responses, args.config)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except ValueError as exc:
        print(f"EvalGate input error: {exc}", file=sys.stderr)
        return 2

    print(f"Suite: {report['suite']} ({report['total_cases']} cases)")
    print(f"Status: {report['status']}")
    print(f"Passed: {report['passed_cases']} | Failed: {report['failed_cases']}")
    print(f"Report: {args.output}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
