"""Small Rule-Based parameter calibration experiment.

数据性质：preliminary single-hop Python simulation。

用法：
    cd ats-sim
    .venv/bin/python experiments/run_rule_calibration.py --deadline-profile relaxed
    .venv/bin/python experiments/run_rule_calibration.py --deadline-profile strict
    .venv/bin/python experiments/run_rule_calibration.py --all-profiles

输出：
    results/rule_calibration_relaxed.json
    results/rule_calibration_strict.json

说明：
- 目的不是完成最终规则库优化，而是在转向 OMNeT++ 前做一个小型规则参数预标定。
- 重点验证：当前场景下是否应更快提高 CIR、减少 CBS 增长。
- 所有结果均为 preliminary，用于指导后续 OMNeT++/INET 迁移和规则库标定。
"""
import argparse
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

from run_rule_compare import default_rule_params, load_cfg, run_once, strip_large
from src.provenance import build_provenance


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results")
TRAFFIC_CONFIG = os.path.join(ROOT, "config", "traffic_literature.yaml")
SCENARIO_CONFIG = os.path.join(ROOT, "config", "scenario_literature.yaml")


def build_calibration_provenance(deadline_profile: str, seed: int, argv) -> dict:
    root = Path(ROOT)
    return build_provenance(
        root=root,
        entry_script=Path(__file__).resolve(),
        seed=seed,
        deadline_profile=deadline_profile,
        config_paths=[Path(TRAFFIC_CONFIG), Path(SCENARIO_CONFIG)],
        source_paths=list((root / "src").glob("*.py")) + [
            root / "experiments" / "run_rule_compare.py",
            Path(__file__).resolve(),
        ],
        argv=argv,
    )


def build_variants(ats: dict, deadline_default: float):
    base = default_rule_params(ats, deadline_default)
    return [
        (
            "Current-Rule",
            "Current R1-R6 engineering defaults after R4 hysteresis fix.",
            base,
        ),
        (
            "Aggressive-CIR",
            "Increase CIR faster and sample more frequently; keep CBS growth moderate.",
            replace(base, cir_up=8e6, cbs_up=10e3, cooldown=0.025, return_ratio=0.12),
        ),
        (
            "CIR-Focused-Low-CBS",
            "Bias adaptation toward CIR rather than CBS, motivated by Offline-Optimized 50Mbps/10Kbit result.",
            replace(base, cir_up=12e6, cbs_up=5e3, cooldown=0.02, warn_ratio=0.7,
                    cbs_delta_max=20e3, return_ratio=0.08),
        ),
        (
            "Conservative-Return",
            "Keep expansions longer by slowing R6 return and R4 downscaling.",
            replace(base, cir_up=8e6, cbs_up=10e3, cooldown=0.025, cir_down=0.5e6,
                    hold_after_expand=0.35, low_load_windows_for_down=12, return_ratio=0.05),
        ),
    ]


def compact_result(result: dict) -> dict:
    r = strip_large(result)
    if r.get("rule_summary"):
        r["rule_summary"] = dict(r["rule_summary"])
    return r


def score(result: dict) -> tuple:
    """Lower is better; used only for ordering preliminary variants."""
    return (
        result.get("deadline_violation_rate", 1.0),
        result.get("drop_rate", 1.0),
        result.get("tt_et_p99_delay_ms", 1e18),
        result.get("cir", 1e18),
        result.get("cbs", 1e18),
    )


def run_calibration(deadline_profile: str, seed: int = 42, argv=()) -> dict:
    traffic_cfg = load_cfg(TRAFFIC_CONFIG)
    scenario_cfg = load_cfg(SCENARIO_CONFIG)
    ats = traffic_cfg["ats"]
    deadline_default = traffic_cfg["deadline"]["D_max"]
    static_low = traffic_cfg["baselines"]["static_low"]

    results = []
    for label, description, params in build_variants(ats, deadline_default):
        print(f"[{deadline_profile}] Running {label}: {description}")
        result = run_once(label, True, traffic_cfg, scenario_cfg,
                          static_low["cir"], static_low["cbs"], deadline_profile,
                          rule_params=params, seed=seed)
        compact = compact_result(result)
        compact["variant_description"] = description
        compact["calibration_score"] = list(score(compact))
        results.append(compact)

    ranked = sorted(results, key=score)
    return {
        "schema_version": "preliminary-ats-poc-v1",
        "provenance": build_calibration_provenance(deadline_profile, seed, argv),
        "note": (
            "Preliminary single-hop Python simulation. This is a small Rule-Based "
            "parameter calibration/ablation experiment before OMNeT++ migration; it is "
            "not final rule optimization."
        ),
        "deadline_profile": deadline_profile,
        "traffic_config": "config/traffic_literature.yaml",
        "scenario_config": "config/scenario_literature.yaml",
        "motivation": (
            "Offline-Optimized selected 50Mbps/10Kbit, while current Rule-Based ended around "
            "26.4Mbps/131.8Kbit. Variants test whether faster CIR growth and reduced CBS "
            "growth improve the preliminary rule behavior."
        ),
        "ranking": [
            "deadline_violation_rate",
            "drop_rate",
            "tt_et_p99_delay_ms",
            "final_cir",
            "final_cbs",
        ],
        "best": ranked[0] if ranked else None,
        "results": ranked,
    }


def save_result(data: dict) -> str:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, f"rule_calibration_{data['deadline_profile']}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return path


def print_summary(data: dict, path: str):
    print("=" * 72)
    print("Small Rule-Based calibration experiment")
    print(f"deadline profile: {data['deadline_profile']}")
    print("注意：preliminary PoC；用于中期前规则库预标定，不是最终优化")
    print("=" * 72)
    for i, r in enumerate(data["results"], 1):
        summary = r.get("rule_summary") or {}
        print(f"\n{i}. [{r['label']}]")
        print(f"  final CIR/CBS:   {r['cir']/1e6:.1f} Mbps / {r['cbs']/1e3:.1f} Kbit")
        print(f"  drop rate:       {r['drop_rate']*100:.2f}%")
        print(f"  TT/ET P95/P99:   {r['tt_et_p95_delay_ms']:.3f} / {r['tt_et_p99_delay_ms']:.3f} ms")
        print(f"  violation rate:  {r['deadline_violation_rate']*100:.2f}%")
        if summary:
            print(f"  adjustments:     {summary['n_adjustments']} {summary['rule_counts']}")
    print(f"\nSaved: {path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Preliminary Rule-Based calibration experiment")
    parser.add_argument("--deadline-profile", choices=["strict", "relaxed"], default="relaxed")
    parser.add_argument("--all-profiles", action="store_true")
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for BE arrivals and ET burst offsets (default: 42).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    profiles = ["relaxed", "strict"] if args.all_profiles else [args.deadline_profile]
    for profile in profiles:
        data = run_calibration(profile, seed=args.seed, argv=sys.argv[1:])
        path = save_result(data)
        print_summary(data, path)


if __name__ == "__main__":
    main()
