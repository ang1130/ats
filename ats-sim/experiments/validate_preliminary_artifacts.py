#!/usr/bin/env python3
"""Validate the dependency chain of preliminary ATS PoC artifacts."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGURES = RESULTS / "figures"
PROFILES = ("relaxed", "strict")
EXPECTED_LABELS = {"Static-Low", "Static-High", "Offline-Optimized", "Rule-Based"}


def load_json(path: Path) -> dict:
    with path.open() as handle:
        return json.load(handle)


def check(condition: bool, message: str, errors: list[str]):
    if not condition:
        errors.append(message)


def check_finite(value, context: str, errors: list[str]):
    check(isinstance(value, (int, float)) and math.isfinite(value), f"{context}: expected finite number", errors)


def validate_profile(profile: str, strict_provenance: bool, errors: list[str], warnings: list[str]):
    grid_path = RESULTS / f"offline_grid_literature_{profile}.json"
    compare_path = RESULTS / f"rule_compare_with_offline_{profile}.json"
    calibration_path = RESULTS / f"rule_calibration_{profile}.json"
    for path in (grid_path, compare_path, calibration_path):
        check(path.exists(), f"Missing artifact: {path.relative_to(ROOT)}", errors)
    if not all(path.exists() for path in (grid_path, compare_path, calibration_path)):
        return

    grid = load_json(grid_path)
    compare = load_json(compare_path)
    calibration = load_json(calibration_path)
    for name, data in (("grid", grid), ("comparison", compare), ("calibration", calibration)):
        check(data.get("deadline_profile") == profile, f"{name} profile mismatch for {profile}", errors)

    best = grid.get("best") or {}
    selected = compare.get("offline_candidate") or {}
    check(best.get("candidate_id") == selected.get("candidate_id"), f"{profile}: comparison Offline candidate differs from grid best", errors)
    check(best.get("cir") == selected.get("cir") and best.get("cbs") == selected.get("cbs"), f"{profile}: comparison Offline CIR/CBS differs from grid best", errors)

    objective = grid.get("objective", {}).get("feasible_if", {})
    check(objective.get("drop_rate_lte") == 0.0, f"{profile}: unexpected grid drop feasibility threshold", errors)
    check(objective.get("deadline_violation_rate_lte") == 0.01, f"{profile}: unexpected grid epsilon", errors)

    labels = {result.get("label") for result in compare.get("results", [])}
    check(labels == EXPECTED_LABELS, f"{profile}: expected comparison labels {sorted(EXPECTED_LABELS)}, got {sorted(labels)}", errors)
    for result in compare.get("results", []):
        for key in ("drop_rate", "deadline_violation_rate", "tt_et_p99_delay_ms"):
            check_finite(result.get(key), f"{profile}/{result.get('label')}/{key}", errors)

    check(calibration.get("best") is not None, f"{profile}: calibration best result missing", errors)
    check(len(calibration.get("results", [])) == 4, f"{profile}: expected four calibration variants", errors)

    for figure_name in (
        f"metrics_bar_{profile}.svg",
        f"delay_timeseries_{profile}.svg",
        f"rule_timeline_{profile}.svg",
        f"cir_cbs_trajectory_{profile}.svg",
    ):
        figure_path = FIGURES / figure_name
        check(figure_path.exists(), f"Missing figure: {figure_path.relative_to(ROOT)}", errors)
        if figure_path.exists():
            text = figure_path.read_text()
            check(
                "preliminary" in text.lower() or "proof-of-concept" in text.lower() or "poc" in text.lower(),
                f"{figure_name}: preliminary boundary note missing",
                errors,
            )
            if strict_provenance:
                run_id = compare.get("provenance", {}).get("run_id")
                check(run_id in text, f"{figure_name}: comparison run ID metadata missing", errors)

    grid_provenance = grid.get("provenance")
    compare_provenance = compare.get("provenance")
    calibration_provenance = calibration.get("provenance")
    if strict_provenance:
        for name, provenance in (("grid", grid_provenance), ("comparison", compare_provenance), ("calibration", calibration_provenance)):
            check(isinstance(provenance, dict), f"{profile}: {name} provenance missing", errors)
            if isinstance(provenance, dict):
                for key in ("run_id", "seed", "config_sha256", "source_sha256", "runtime", "git"):
                    check(key in provenance, f"{profile}: {name} provenance missing {key}", errors)
        if isinstance(grid_provenance, dict) and isinstance(compare_provenance, dict):
            for key in ("seed", "deadline_profile", "config_sha256"):
                check(grid_provenance.get(key) == compare_provenance.get(key), f"{profile}: grid/comparison provenance mismatch in {key}", errors)
    elif not all(isinstance(item, dict) for item in (grid_provenance, compare_provenance, calibration_provenance)):
        warnings.append(f"{profile}: legacy artifacts lack complete provenance; rerun the pipeline for strict provenance validation.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate preliminary ATS PoC artifacts")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--legacy", action="store_true", help="Validate legacy artifacts without requiring provenance.")
    mode.add_argument("--strict-provenance", action="store_true", help="Require provenance produced by current scripts.")
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    for profile in PROFILES:
        validate_profile(profile, args.strict_provenance, errors, warnings)

    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        print("Artifact validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("Artifact validation passed for relaxed and strict profiles.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
