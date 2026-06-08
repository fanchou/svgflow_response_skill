#!/usr/bin/env python3
"""
Run one production pipeline fixture through package validators.

This helper validates the shipping response-to-DSL-to-artifact path for a fixture.
It does not generate new artwork; it proves that a real or inline assistant
response is connected to an expected DSL fixture, an expected rendered output,
and the validator set required before using that output.
"""

from __future__ import annotations

import argparse
import importlib.util
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
        raise SystemExit("[FAIL] production pipeline cases must contain cases[]")
    for case in cases:
        if isinstance(case, dict) and case.get("id") == case_id:
            return case
    raise SystemExit(f"[FAIL] unknown production pipeline case: {case_id}")


def validate_case(root: Path, case: dict[str, Any]) -> None:
    validator = load_validate_module(root)
    validator.require(hasattr(validator, "PIPELINE_VALIDATORS"), "validator module missing PIPELINE_VALIDATORS")

    input_file = case.get("inputFile")
    inline_input = case.get("input")
    if isinstance(input_file, str):
        input_path = root / input_file
        validator.require(input_path.exists(), f"missing input file: {input_path}")
        validator.require(input_path.read_text(encoding="utf-8").strip(), f"empty input file: {input_path}")
    else:
        validator.require(isinstance(inline_input, str) and inline_input.strip(), "pipeline case input is required")

    dsl_path = root / str(case.get("dsl"))
    validator.require(dsl_path.exists(), f"missing DSL fixture: {dsl_path}")
    svg_path = None
    html_path = None
    if isinstance(case.get("svg"), str):
        svg_path = root / str(case.get("svg"))
        validator.require(svg_path.exists(), f"missing SVG fixture: {svg_path}")
    if isinstance(case.get("html"), str):
        html_path = root / str(case.get("html"))
        validator.require(html_path.exists(), f"missing HTML fixture: {html_path}")
    validator.require(svg_path is not None or html_path is not None, "pipeline case requires an SVG or HTML fixture")

    validators = case.get("validators")
    validator.require(isinstance(validators, list) and validators, "pipeline case validators are required")
    validator.run_pipeline_validators(validators, dsl_path, svg_path=svg_path, html_path=html_path)

    dsl = validator.read_json(dsl_path)
    validator.require(isinstance(dsl, dict), f"{dsl_path} must contain a JSON object")
    if isinstance(case.get("expectedLayoutIntent"), str):
        layout = dsl.get("layout", {})
        validator.require(
            isinstance(layout, dict) and layout.get("intent") == case.get("expectedLayoutIntent"),
            f"{dsl_path} layout intent does not match pipeline case",
        )
    expected_diagram_type = case.get("expectedDiagramType")
    if expected_diagram_type in {"interactive_walkthrough", "module_grid"}:
        meta = dsl.get("meta", {})
        validator.require(
            isinstance(meta, dict) and meta.get("diagramType") == expected_diagram_type,
            f"{dsl_path} diagram type does not match pipeline case",
        )
    validator.ok(f"Pipeline fixture checks passed: {case['id']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate one production pipeline fixture.")
    parser.add_argument("--root", default=".", help="Package root")
    parser.add_argument("--case", required=True, help="Production pipeline case id")
    args = parser.parse_args()

    root = Path(args.root)
    data = read_json(root / "tests" / "production_pipeline_cases.json")
    validate_case(root, select_case(data, args.case))


if __name__ == "__main__":
    main()
