#!/usr/bin/env python3
"""
Run one repair-signal fixture and print the mapped repair action.

The fixture must fail validation with the expected signal. The signal must map
to a repair rule and concrete action list before the package can be considered
release-ready.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
from pathlib import Path
from typing import Any


def load_validate_module(root: Path) -> Any:
    validator_path = root / "scripts" / "validate_svg.py"
    spec = importlib.util.spec_from_file_location("svgflow_validate_svg", validator_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"[FAIL] unable to load validator module: {validator_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"[FAIL] {path} must contain a JSON object")
    return data


def select_case(data: dict[str, Any], case_id: str) -> dict[str, Any]:
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise SystemExit("[FAIL] repair signal cases must contain cases[]")
    for case in cases:
        if isinstance(case, dict) and case.get("id") == case_id:
            return case
    raise SystemExit(f"[FAIL] unknown repair signal case: {case_id}")


def run_expected_failure(validator: Any, case: dict[str, Any], root: Path) -> str:
    validators = {
        "infographic_svg": validator.validate_infographic_svg,
        "visual_quality": validator.validate_visual_quality_svg,
    }
    validator_name = case.get("validator")
    validator_fn = validators.get(validator_name)
    validator.require(validator_fn is not None, f"unknown repair validator: {validator_name}")
    fixture_path = root / str(case.get("fixture"))
    validator.require(fixture_path.exists(), f"missing repair fixture: {fixture_path}")

    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            validator_fn(fixture_path)
    except SystemExit as exc:
        output = buffer.getvalue()
        validator.require(exc.code != 0, f"{fixture_path} unexpectedly passed")
        validator.require(case["failureSignal"] in output, f"{fixture_path} did not emit expected repair signal")
        return output
    raise SystemExit(f"[FAIL] {fixture_path} passed; expected repair signal {case['failureSignal']}")


def validate_case(root: Path, case: dict[str, Any]) -> None:
    validator = load_validate_module(root)
    for key in ["failureSignal", "repairRule"]:
        validator.require(isinstance(case.get(key), str) and case[key].strip(), f"repair case missing {key}")
    actions = case.get("repairActions")
    validator.require(isinstance(actions, list) and len(actions) >= 2, "repair case needs at least two repairActions")
    for action in actions:
        validator.require(isinstance(action, str) and action.strip(), "repair action must be a non-empty string")

    output = run_expected_failure(validator, case, root)
    validator.ok(f"Repair signal checks passed: {case['id']}")
    print(f"signal: {case['failureSignal']}")
    print(f"rule: {case['repairRule']}")
    print(f"firstAction: {actions[0]}")
    print(output.strip().splitlines()[0])


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate one repair-signal fixture.")
    parser.add_argument("--root", default=".", help="Package root")
    parser.add_argument("--case", required=True, help="Repair signal case id")
    args = parser.parse_args()

    root = Path(args.root)
    data = read_json(root / "tests" / "repair_signal_cases.json")
    validate_case(root, select_case(data, args.case))


if __name__ == "__main__":
    main()
