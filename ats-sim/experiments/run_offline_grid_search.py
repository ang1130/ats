"""Offline-Optimized CIR/CBS grid search for the literature-based ATS PoC.

数据性质：preliminary single-hop Python simulation。

用法：
    cd ats-sim
    .venv/bin/python experiments/run_offline_grid_search.py --deadline-profile relaxed
    .venv/bin/python experiments/run_offline_grid_search.py --deadline-profile strict
    .venv/bin/python experiments/run_offline_grid_search.py --all-profiles

输出：
    results/offline_grid_literature_relaxed.json
    results/offline_grid_literature_strict.json

说明：
- 使用 traffic_literature.yaml 和 scenario_literature.yaml。
- 仅搜索 CIR/CBS；MRT 固定，不参与当前 Python PoC 的在线/离线优化。
- Offline-Optimized 是离散网格搜索近似，不是文献中的完整 Downhill Simplex。
"""
import argparse
import json
import math
import os
from typing import Dict, List, Tuple

from run_rule_compare import load_cfg, run_once, strip_large


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAFFIC_CONFIG = os.path.join(ROOT, "config", "traffic_literature.yaml")
SCENARIO_CONFIG = os.path.join(ROOT, "config", "scenario_literature.yaml")
RESULTS_DIR = os.path.join(ROOT, "results")


METRIC_KEYS = [
    "label",
    "duration",
    "cir",
    "cbs",
    "n_generated",
    "n_dropped",
    "drop_rate",
    "mean_delay_ms",
    "p95_delay_ms",
    "p99_delay_ms",
    "tt_et_mean_delay_ms",
    "tt_et_p95_delay_ms",
    "tt_et_p99_delay_ms",
    "be_mean_delay_ms",
    "deadline_violation_rate",
    "deadline_violations",
    "n_tt_et",
    "throughput_mbps",
    "initial_cir",
    "initial_cbs",
]


def candidate_id(cir: float, cbs: float) -> str:
    return f"cir_{cir / 1e6:.1f}Mbps_cbs_{cbs / 1e3:.1f}Kbit"


def finite_or_large(value: float) -> float:
    if value is None:
        return 1e18
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return 1e18
    return value


def resource_score(cir: float, cbs: float, traffic_cfg: dict, cbs_candidates: List[float]) -> float:
    link_bw = traffic_cfg["link"]["bandwidth"]
    max_cbs = max(cbs_candidates) if cbs_candidates else max(cbs, 1.0)
    return cir / link_bw + 0.1 * (cbs / max_cbs)


def compact_metrics(result: dict) -> dict:
    stripped = strip_large(result)
    return {k: stripped.get(k) for k in METRIC_KEYS if k in stripped}


def rank_tuple(result: dict, feasible: bool, score: float) -> Tuple[float, ...]:
    drop = finite_or_large(result.get("drop_rate", 1.0))
    violation = finite_or_large(result.get("deadline_violation_rate", 1.0))
    p99 = finite_or_large(result.get("tt_et_p99_delay_ms", 1e18))
    if feasible:
        return (0, score, p99, drop, violation)
    return (1, violation, drop, p99, score)


def make_candidate(result: dict, cir: float, cbs: float, traffic_cfg: dict,
                   cbs_candidates: List[float], epsilon: float, max_drop_rate: float) -> dict:
    score = resource_score(cir, cbs, traffic_cfg, cbs_candidates)
    drop = finite_or_large(result.get("drop_rate", 1.0))
    violation = finite_or_large(result.get("deadline_violation_rate", 1.0))
    feasible = drop <= max_drop_rate and violation <= epsilon
    rank = rank_tuple(result, feasible, score)
    return {
        "candidate_id": candidate_id(cir, cbs),
        "feasible": feasible,
        "rank_tuple": list(rank),
        "resource_score": score,
        "cir": cir,
        "cbs": cbs,
        "metrics": compact_metrics(result),
    }


def run_grid(deadline_profile: str, top_k: int = 5) -> dict:
    traffic_cfg = load_cfg(TRAFFIC_CONFIG)
    scenario_cfg = load_cfg(SCENARIO_CONFIG)

    search_space = traffic_cfg["baselines"]["offline_optimized_search_space"]
    cir_candidates = search_space["cir_candidates"]
    cbs_candidates = search_space["cbs_candidates"]
    mrt_fixed = traffic_cfg["ats"].get("mrt_fixed")
    epsilon = traffic_cfg.get("deadline", {}).get("epsilon", 0.01)
    max_drop_rate = 0.0

    candidates = []
    total = len(cir_candidates) * len(cbs_candidates)
    done = 0
    for cir in cir_candidates:
        for cbs in cbs_candidates:
            done += 1
            label = f"Offline-Candidate {cir / 1e6:.1f}Mbps/{cbs / 1e3:.1f}Kbit"
            print(f"[{deadline_profile}] {done:02d}/{total}: {label}")
            result = run_once(label, False, traffic_cfg, scenario_cfg, cir, cbs, deadline_profile)
            candidates.append(make_candidate(result, cir, cbs, traffic_cfg, cbs_candidates,
                                             epsilon, max_drop_rate))

    candidates.sort(key=lambda c: tuple(c["rank_tuple"]))
    best = dict(candidates[0]) if candidates else None
    if best:
        best["label"] = "Offline-Optimized"

    return {
        "note": (
            "Preliminary single-hop Python simulation. Offline-Optimized is a CIR/CBS "
            "grid-search approximation of a static optimized ATS baseline; MRT is fixed "
            "and not searched in the current PoC."
        ),
        "deadline_profile": deadline_profile,
        "traffic_config": "config/traffic_literature.yaml",
        "scenario_config": "config/scenario_literature.yaml",
        "search_space": {
            "cir_candidates": cir_candidates,
            "cbs_candidates": cbs_candidates,
            "mrt_fixed": mrt_fixed,
        },
        "objective": {
            "feasible_if": {
                "drop_rate_lte": max_drop_rate,
                "deadline_violation_rate_lte": epsilon,
            },
            "resource_score": "cir/link_bandwidth + 0.1*(cbs/max_cbs_candidate)",
            "ranking": {
                "feasible": [
                    "resource_score",
                    "tt_et_p99_delay_ms",
                    "drop_rate",
                    "deadline_violation_rate",
                ],
                "infeasible": [
                    "deadline_violation_rate",
                    "drop_rate",
                    "tt_et_p99_delay_ms",
                    "resource_score",
                ],
            },
        },
        "best": best,
        "top_k": candidates[:top_k],
        "candidates": candidates,
    }


def save_result(result: dict) -> str:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, f"offline_grid_literature_{result['deadline_profile']}.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    return out_path


def print_summary(result: dict, out_path: str):
    best = result["best"]
    print("=" * 72)
    print("Offline-Optimized CIR/CBS grid search")
    print("配置：traffic_literature.yaml + scenario_literature.yaml")
    print(f"deadline profile: {result['deadline_profile']}")
    print(f"candidates: {len(result['candidates'])}")
    print("注意：preliminary single-hop Python PoC；MRT 固定，未参与搜索")
    print("=" * 72)

    if not best:
        print("No candidates evaluated.")
        print(f"Saved: {out_path}")
        return

    metrics = best["metrics"]
    print("\nBest candidate:")
    print(f"  candidate_id:     {best['candidate_id']}")
    print(f"  CIR/CBS:          {best['cir'] / 1e6:.1f} Mbps / {best['cbs'] / 1e3:.1f} Kbit")
    print(f"  feasible:         {best['feasible']}")
    print(f"  resource_score:   {best['resource_score']:.4f}")
    print(f"  drop rate:        {metrics['drop_rate'] * 100:.2f}%")
    print(f"  TT/ET P95/P99:    {metrics['tt_et_p95_delay_ms']:.3f} / {metrics['tt_et_p99_delay_ms']:.3f} ms")
    print(f"  violation rate:   {metrics['deadline_violation_rate'] * 100:.2f}%")

    print("\nTop candidates:")
    for i, cand in enumerate(result["top_k"], 1):
        m = cand["metrics"]
        print(
            f"  {i}. {cand['candidate_id']} | feasible={cand['feasible']} | "
            f"drop={m['drop_rate'] * 100:.2f}% | "
            f"viol={m['deadline_violation_rate'] * 100:.2f}% | "
            f"p99={m['tt_et_p99_delay_ms']:.3f} ms | "
            f"score={cand['resource_score']:.4f}"
        )
    print(f"\nSaved: {out_path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Preliminary Offline-Optimized ATS CIR/CBS grid search")
    parser.add_argument(
        "--deadline-profile",
        choices=["strict", "relaxed"],
        default="relaxed",
        help="strict 使用文献 350us/600us deadline；relaxed 统一使用 10ms D_max",
    )
    parser.add_argument(
        "--all-profiles",
        action="store_true",
        help="Run both relaxed and strict profiles.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of top candidates to include in the summary list.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    profiles = ["relaxed", "strict"] if args.all_profiles else [args.deadline_profile]
    for profile in profiles:
        result = run_grid(profile, top_k=args.top_k)
        out_path = save_result(result)
        print_summary(result, out_path)


if __name__ == "__main__":
    main()
