"""Four-method comparison with Offline-Optimized baseline.

数据性质：preliminary single-hop Python simulation。

用法：
    cd ats-sim
    .venv/bin/python experiments/run_compare_with_offline.py --deadline-profile relaxed
    .venv/bin/python experiments/run_compare_with_offline.py --deadline-profile strict

输出：
    results/rule_compare_with_offline_relaxed.json
    results/rule_compare_with_offline_strict.json

说明：
- 在 Static-Low / Static-High / Rule-Based 之外，加入由
  run_offline_grid_search.py 选出的 Offline-Optimized 静态基线。
- Offline-Optimized 是离散 CIR/CBS 网格搜索得到的 preliminary baseline，MRT 固定。
"""
import argparse
import json
import os
import sys
from pathlib import Path

from run_rule_compare import load_cfg, run_once
from src.provenance import build_provenance, same_experiment_inputs


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results")
TRAFFIC_CONFIG = os.path.join(ROOT, "config", "traffic_literature.yaml")
SCENARIO_CONFIG = os.path.join(ROOT, "config", "scenario_literature.yaml")


def build_compare_provenance(deadline_profile: str, seed: int, argv) -> dict:
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


def load_offline_best(deadline_profile: str, expected_provenance: dict | None = None) -> dict:
    path = os.path.join(RESULTS_DIR, f"offline_grid_literature_{deadline_profile}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Missing {path}. Run: .venv/bin/python experiments/run_offline_grid_search.py "
            f"--deadline-profile {deadline_profile}"
        )
    with open(path) as f:
        data = json.load(f)
    if expected_provenance is not None:
        offline_provenance = data.get("provenance")
        if offline_provenance is None:
            raise ValueError(
                f"{path} has no provenance metadata. Rerun the offline grid search with the same seed first."
            )
        if not same_experiment_inputs(offline_provenance, expected_provenance):
            raise ValueError(
                f"{path} does not match the requested profile, seed, or input configuration. "
                "Rerun the offline grid search before comparison."
            )
    best = data.get("best")
    if not best:
        raise ValueError(f"No best candidate found in {path}")
    return best


def strip_for_print(result: dict) -> dict:
    r = dict(result)
    r.pop("monitor_samples", None)
    r.pop("rule_logs", None)
    return r


def run_compare(deadline_profile: str, seed: int = 42, argv=()) -> dict:
    traffic_cfg = load_cfg(TRAFFIC_CONFIG)
    scenario_cfg = load_cfg(SCENARIO_CONFIG)
    provenance = build_compare_provenance(deadline_profile, seed, argv)
    baselines = traffic_cfg["baselines"]
    static_low = baselines["static_low"]
    static_high = baselines["static_high"]
    offline_best = load_offline_best(deadline_profile, expected_provenance=provenance)

    results = []
    results.append(run_once("Static-Low", False, traffic_cfg, scenario_cfg,
                            static_low["cir"], static_low["cbs"], deadline_profile, seed=seed))
    results.append(run_once("Static-High", False, traffic_cfg, scenario_cfg,
                            static_high["cir"], static_high["cbs"], deadline_profile, seed=seed))
    results.append(run_once("Offline-Optimized", False, traffic_cfg, scenario_cfg,
                            offline_best["cir"], offline_best["cbs"], deadline_profile, seed=seed))
    results.append(run_once("Rule-Based", True, traffic_cfg, scenario_cfg,
                            static_low["cir"], static_low["cbs"], deadline_profile, seed=seed))

    return {
        "schema_version": "preliminary-ats-poc-v1",
        "provenance": provenance,
        "note": (
            "Preliminary single-hop Python simulation. Offline-Optimized is selected "
            "by CIR/CBS grid search; Rule-Based thresholds are engineering defaults, "
            "not fully calibrated. MRT is a configuration placeholder and is not enforced "
            "by the current execution model."
        ),
        "deadline_profile": deadline_profile,
        "offline_source": f"results/offline_grid_literature_{deadline_profile}.json",
        "offline_candidate": {
            "candidate_id": offline_best.get("candidate_id"),
            "feasible": offline_best.get("feasible"),
            "resource_score": offline_best.get("resource_score"),
            "cir": offline_best["cir"],
            "cbs": offline_best["cbs"],
        },
        "results": results,
    }


def save_result(result: dict) -> str:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, f"rule_compare_with_offline_{result['deadline_profile']}.json")
    with open(path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    return path


def print_summary(result: dict, path: str):
    print("=" * 72)
    print("Preliminary Static-Low / Static-High / Offline-Optimized / Rule-Based comparison")
    print("配置：traffic_literature.yaml + scenario_literature.yaml")
    print(f"deadline profile: {result['deadline_profile']}")
    offline = result["offline_candidate"]
    print(
        "Offline source: "
        f"{offline['candidate_id']} | feasible={offline['feasible']} | "
        f"score={offline['resource_score']:.4f}"
    )
    print("注意：结果仅为 preliminary single-hop Python PoC")
    print("=" * 72)
    for r in result["results"]:
        print(f"\n[{r['label']}]")
        print(f"  initial CIR/CBS: {r['initial_cir']/1e6:.1f} Mbps / {r['initial_cbs']/1e3:.1f} Kbit")
        print(f"  final   CIR/CBS: {r['cir']/1e6:.1f} Mbps / {r['cbs']/1e3:.1f} Kbit")
        print(f"  generated/drop:  {r['n_generated']} / {r['n_dropped']} ({r['drop_rate']*100:.2f}%)")
        print(f"  TT/ET P95/P99:   {r['tt_et_p95_delay_ms']:.3f} / {r['tt_et_p99_delay_ms']:.3f} ms")
        print(f"  violation rate:  {r['deadline_violation_rate']*100:.2f}% ({r['deadline_violations']}/{r['n_tt_et']})")
        if r["rule_summary"]:
            print(f"  rule adjustments: {r['rule_summary']['n_adjustments']} {r['rule_summary']['rule_counts']}")
    print(f"\nSaved: {path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Preliminary ATS comparison with Offline-Optimized baseline")
    parser.add_argument(
        "--deadline-profile",
        choices=["strict", "relaxed"],
        default="relaxed",
        help="strict 使用文献 350us/600us deadline；relaxed 统一使用 10ms D_max",
    )
    parser.add_argument("--all-profiles", action="store_true", help="Run both relaxed and strict profiles.")
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
        result = run_compare(profile, seed=args.seed, argv=sys.argv[1:])
        path = save_result(result)
        print_summary(result, path)


if __name__ == "__main__":
    main()
