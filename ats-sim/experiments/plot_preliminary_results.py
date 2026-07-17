"""Generate preliminary mid-term figures for ATS PoC results.

数据性质：preliminary single-hop Python simulation。

用法：
    cd ats-sim
    .venv/bin/python experiments/plot_preliminary_results.py --deadline-profile relaxed
    .venv/bin/python experiments/plot_preliminary_results.py --deadline-profile strict

输出：
    results/figures/metrics_bar_<profile>.svg
    results/figures/delay_timeseries_<profile>.svg
    results/figures/rule_timeline_<profile>.svg
    results/figures/cir_cbs_trajectory_<profile>.svg

说明：
- 不依赖 matplotlib，直接生成 SVG，便于放入中期报告/PPT。
- 图中所有数据均应标注 preliminary。
"""
import argparse
import json
import math
import os
from html import escape
from typing import Callable, Dict, List, Tuple


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results")
FIG_DIR = os.path.join(RESULTS_DIR, "figures")

PALETTE = {
    "Static-Low": "#2a78d6",
    "Static-High": "#1baf7a",
    "Offline-Optimized": "#eda100",
    "Rule-Based": "#008300",
}

DARK_PALETTE = {
    "Static-Low": "#3987e5",
    "Static-High": "#199e70",
    "Offline-Optimized": "#c98500",
    "Rule-Based": "#008300",
}

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
TEXT_MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"


class SVG:
    def __init__(self, width: int, height: int, title: str):
        self.width = width
        self.height = height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
            "<style>",
            "text{font-family:system-ui,-apple-system,Segoe UI,sans-serif}",
            ".title{font-size:18px;font-weight:700;fill:#0b0b0b}",
            ".subtitle{font-size:12px;fill:#52514e}",
            ".axis{font-size:11px;fill:#898781}",
            ".label{font-size:11px;fill:#0b0b0b}",
            ".legend{font-size:12px;fill:#52514e}",
            ".note{font-size:11px;fill:#898781}",
            "</style>",
            f'<rect width="100%" height="100%" fill="{SURFACE}" rx="14"/>',
        ]

    def add(self, text: str):
        self.parts.append(text)

    def finish(self) -> str:
        return "\n".join(self.parts + ["</svg>\n"])


def load_compare(profile: str) -> dict:
    path = os.path.join(RESULTS_DIR, f"rule_compare_with_offline_{profile}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Missing {path}. Run experiments/run_compare_with_offline.py --deadline-profile {profile} first."
        )
    with open(path) as f:
        return json.load(f)


def ensure_fig_dir():
    os.makedirs(FIG_DIR, exist_ok=True)


def write_svg(name: str, svg: SVG):
    ensure_fig_dir()
    path = os.path.join(FIG_DIR, name)
    with open(path, "w") as f:
        f.write(svg.finish())
    return path


def safe_max(values: List[float], fallback: float = 1.0) -> float:
    vals = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    return max(vals) if vals else fallback


def add_artifact_metadata(svg: SVG, data: dict, profile: str):
    provenance = data.get("provenance", {})
    run_id = provenance.get("run_id", "legacy-no-provenance")
    seed = provenance.get("seed", "legacy-unknown")
    svg.add(
        "<metadata>"
        f"preliminary-ats-poc; profile={escape(str(profile))}; seed={escape(str(seed))}; "
        f"source_run_id={escape(str(run_id))}"
        "</metadata>"
    )


def legend(svg: SVG, labels: List[str], x: float, y: float):
    cur_x = x
    for label in labels:
        color = PALETTE.get(label, "#52514e")
        svg.add(f'<rect x="{cur_x:.1f}" y="{y - 9:.1f}" width="12" height="12" rx="3" fill="{color}"/>')
        svg.add(f'<text class="legend" x="{cur_x + 18:.1f}" y="{y + 1:.1f}">{escape(label)}</text>')
        cur_x += 18 + len(label) * 7.4 + 18


def metric_value(result: dict, key: str) -> float:
    value = result.get(key, 0.0)
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0.0
    return value


def plot_metrics_bar(data: dict, profile: str) -> str:
    results = data["results"]
    labels = [r["label"] for r in results]
    metrics = [
        ("Drop rate (%)", lambda r: metric_value(r, "drop_rate") * 100),
        ("Violation (%)", lambda r: metric_value(r, "deadline_violation_rate") * 100),
        ("TT/ET P99 (ms)", lambda r: metric_value(r, "tt_et_p99_delay_ms")),
    ]

    width, height = 1180, 680
    svg = SVG(width, height, f"ATS preliminary metrics bar chart {profile}")
    add_artifact_metadata(svg, data, profile)
    svg.add(f'<text class="title" x="40" y="38">ATS preliminary comparison — {profile}</text>')
    svg.add('<text class="subtitle" x="40" y="60">Static-Low / Static-High / Offline-Optimized / Rule-Based · single-hop Python PoC</text>')
    legend(svg, labels, 40, 92)

    panel_w = 340
    panel_h = 400
    gap = 34
    left0 = 54
    top = 150
    for p_idx, (title, fn) in enumerate(metrics):
        x0 = left0 + p_idx * (panel_w + gap)
        y0 = top
        values = [fn(r) for r in results]
        max_v = safe_max(values)
        axis_max = max_v * 1.15 if max_v > 0 else 1.0
        svg.add(f'<text class="label" x="{x0}" y="{y0 - 20}">{escape(title)}</text>')
        for tick in range(5):
            value = axis_max * tick / 4
            y = y0 + panel_h - panel_h * tick / 4
            svg.add(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0 + panel_w}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>')
            svg.add(f'<text class="axis" x="{x0 - 8}" y="{y + 4:.1f}" text-anchor="end">{value:.1f}</text>')
        svg.add(f'<line x1="{x0}" y1="{y0 + panel_h}" x2="{x0 + panel_w}" y2="{y0 + panel_h}" stroke="{AXIS}"/>')

        bar_gap = 16
        bar_w = (panel_w - bar_gap * (len(results) + 1)) / len(results)
        for i, r in enumerate(results):
            value = values[i]
            bar_h = 0 if axis_max == 0 else panel_h * value / axis_max
            bx = x0 + bar_gap + i * (bar_w + bar_gap)
            by = y0 + panel_h - bar_h
            color = PALETTE.get(r["label"], "#2a78d6")
            svg.add(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" rx="4" fill="{color}">'
                    f'<title>{escape(r["label"])} · {escape(title)}: {value:.3f}</title></rect>')
            svg.add(f'<text class="label" x="{bx + bar_w / 2:.1f}" y="{by - 7:.1f}" text-anchor="middle">{value:.2f}</text>')
            svg.add(f'<text class="axis" transform="translate({bx + bar_w / 2:.1f},{y0 + panel_h + 68:.1f}) rotate(-35)" text-anchor="end">{escape(r["label"])}</text>')

    svg.add('<text class="note" x="40" y="650">Note: preliminary / proof-of-concept data; not final thesis-grade quantitative results.</text>')
    return write_svg(f"metrics_bar_{profile}.svg", svg)


def points_to_path(points: List[Tuple[float, float]]) -> str:
    if not points:
        return ""
    first = points[0]
    rest = " ".join(f"L {x:.1f} {y:.1f}" for x, y in points[1:])
    return f"M {first[0]:.1f} {first[1]:.1f} {rest}"


def plot_delay_timeseries(data: dict, profile: str) -> str:
    results = data["results"]
    labels = [r["label"] for r in results]
    width, height = 1120, 620
    margin = {"l": 74, "r": 36, "t": 120, "b": 78}
    plot_w = width - margin["l"] - margin["r"]
    plot_h = height - margin["t"] - margin["b"]

    all_samples = []
    for r in results:
        for s in r.get("monitor_samples", []):
            all_samples.append(s)
    max_t = safe_max([s.get("t", 0.0) for s in all_samples], 1.0)
    max_delay_ms = safe_max([s.get("d_obs", 0.0) * 1e3 for s in all_samples], 1.0)
    axis_max = max(max_delay_ms * 1.1, 1.0)

    def sx(t): return margin["l"] + plot_w * t / max_t
    def sy(v_ms): return margin["t"] + plot_h - plot_h * v_ms / axis_max

    svg = SVG(width, height, f"ATS delay time series {profile}")
    add_artifact_metadata(svg, data, profile)
    svg.add(f'<text class="title" x="40" y="38">Observed TT/ET delay over time — {profile}</text>')
    svg.add('<text class="subtitle" x="40" y="60">Monitor d_obs = windowed P95 delay · single-hop Python PoC</text>')
    legend(svg, labels, 40, 92)

    for tick in range(6):
        value = axis_max * tick / 5
        y = sy(value)
        svg.add(f'<line x1="{margin["l"]}" y1="{y:.1f}" x2="{width - margin["r"]}" y2="{y:.1f}" stroke="{GRID}"/>')
        svg.add(f'<text class="axis" x="{margin["l"] - 10}" y="{y + 4:.1f}" text-anchor="end">{value:.0f}</text>')
    for tick in range(5):
        t = max_t * tick / 4
        x = sx(t)
        svg.add(f'<text class="axis" x="{x:.1f}" y="{height - 42}" text-anchor="middle">{t:.1f}s</text>')
    svg.add(f'<line x1="{margin["l"]}" y1="{margin["t"] + plot_h}" x2="{width - margin["r"]}" y2="{margin["t"] + plot_h}" stroke="{AXIS}"/>')
    svg.add(f'<line x1="{margin["l"]}" y1="{margin["t"]}" x2="{margin["l"]}" y2="{margin["t"] + plot_h}" stroke="{AXIS}"/>')
    svg.add(f'<text class="axis" x="{margin["l"] - 48}" y="{margin["t"] - 16}">ms</text>')

    for r in results:
        samples = r.get("monitor_samples", [])
        pts = [(sx(s.get("t", 0.0)), sy(s.get("d_obs", 0.0) * 1e3)) for s in samples]
        color = PALETTE.get(r["label"], "#2a78d6")
        svg.add(f'<path d="{points_to_path(pts)}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round">'
                f'<title>{escape(r["label"])} observed delay</title></path>')
        if pts:
            svg.add(f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="4" fill="{color}" stroke="{SURFACE}" stroke-width="2"/>')
            svg.add(f'<text class="label" x="{pts[-1][0] + 8:.1f}" y="{pts[-1][1] + 4:.1f}">{escape(r["label"])}</text>')

    svg.add('<text class="note" x="40" y="590">Note: d_obs is monitor-window P95 delay, not a final standards-compliant ATS measurement.</text>')
    return write_svg(f"delay_timeseries_{profile}.svg", svg)


def plot_rule_timeline(data: dict, profile: str) -> str:
    rule_result = next((r for r in data["results"] if r["label"] == "Rule-Based"), None)
    if not rule_result:
        raise ValueError("Rule-Based result missing")
    logs = rule_result.get("rule_logs", [])
    width, height = 980, 420
    margin = {"l": 136, "r": 34, "t": 105, "b": 62}
    plot_w = width - margin["l"] - margin["r"]
    rules = ["R2_DELAY_WARN", "R3_BURST", "R4_RESOURCE_EXCESS", "R5_DROP", "R6_RETURN"]
    rule_colors = {
        "R2_DELAY_WARN": "#2a78d6",
        "R3_BURST": "#eda100",
        "R4_RESOURCE_EXCESS": "#1baf7a",
        "R5_DROP": "#e34948",
        "R6_RETURN": "#4a3aa7",
    }
    max_t = safe_max([log.get("t", 0.0) for log in logs], 1.0)

    def sx(t): return margin["l"] + plot_w * t / max_t

    svg = SVG(width, height, f"ATS rule trigger timeline {profile}")
    add_artifact_metadata(svg, data, profile)
    svg.add(f'<text class="title" x="40" y="38">Rule trigger timeline — {profile}</text>')
    svg.add('<text class="subtitle" x="40" y="60">Rule-Based adjustments; each marker is one online CIR/CBS action</text>')

    row_gap = 42
    for i, rule in enumerate(rules):
        y = margin["t"] + i * row_gap
        svg.add(f'<text class="axis" x="{margin["l"] - 12}" y="{y + 4}" text-anchor="end">{escape(rule)}</text>')
        svg.add(f'<line x1="{margin["l"]}" y1="{y}" x2="{width - margin["r"]}" y2="{y}" stroke="{GRID}"/>')
    for tick in range(5):
        t = max_t * tick / 4
        x = sx(t)
        svg.add(f'<text class="axis" x="{x:.1f}" y="{height - 30}" text-anchor="middle">{t:.1f}s</text>')

    for log in logs:
        rule = log.get("rule")
        if rule not in rules:
            continue
        y = margin["t"] + rules.index(rule) * row_gap
        x = sx(log.get("t", 0.0))
        color = rule_colors.get(rule, "#52514e")
        svg.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{color}" stroke="{SURFACE}" stroke-width="2">'
                f'<title>{escape(rule)} at t={log.get("t", 0):.3f}s · CIR {log.get("old_cir",0)/1e6:.1f}→{log.get("new_cir",0)/1e6:.1f} Mbps · CBS {log.get("old_cbs",0)/1e3:.1f}→{log.get("new_cbs",0)/1e3:.1f} Kbit</title></circle>')

    counts = rule_result.get("rule_summary", {}).get("rule_counts", {})
    summary = " · ".join(f"{k}: {v}" for k, v in counts.items())
    svg.add(f'<text class="note" x="40" y="390">Counts: {escape(summary)} · preliminary PoC.</text>')
    return write_svg(f"rule_timeline_{profile}.svg", svg)


def plot_cir_cbs_trajectory(data: dict, profile: str) -> str:
    rule_result = next((r for r in data["results"] if r["label"] == "Rule-Based"), None)
    offline = next((r for r in data["results"] if r["label"] == "Offline-Optimized"), None)
    if not rule_result or not offline:
        raise ValueError("Rule-Based or Offline-Optimized result missing")
    logs = rule_result.get("rule_logs", [])
    duration = rule_result.get("duration", 1.0)
    cir_points = [(0.0, rule_result["initial_cir"] / 1e6)]
    cbs_points = [(0.0, rule_result["initial_cbs"] / 1e3)]
    for log in logs:
        t = log.get("t", 0.0)
        cir_points.append((t, log.get("new_cir", rule_result["cir"]) / 1e6))
        cbs_points.append((t, log.get("new_cbs", rule_result["cbs"]) / 1e3))
    cir_points.append((duration, rule_result["cir"] / 1e6))
    cbs_points.append((duration, rule_result["cbs"] / 1e3))

    width, height = 1060, 620
    margin = {"l": 72, "r": 48, "t": 110, "b": 72}
    panel_h = 180
    panel_gap = 54
    plot_w = width - margin["l"] - margin["r"]
    max_t = duration

    def sx(t): return margin["l"] + plot_w * t / max_t

    svg = SVG(width, height, f"ATS CIR CBS trajectory {profile}")
    add_artifact_metadata(svg, data, profile)
    svg.add(f'<text class="title" x="40" y="38">Rule-Based CIR/CBS trajectory — {profile}</text>')
    svg.add('<text class="subtitle" x="40" y="60">Online rule updates compared with Offline-Optimized static reference</text>')

    def panel(points, y0, title, unit, offline_value, color, axis_max):
        def sy(v): return y0 + panel_h - panel_h * v / axis_max
        svg.add(f'<text class="label" x="{margin["l"]}" y="{y0 - 18}">{escape(title)}</text>')
        for tick in range(5):
            value = axis_max * tick / 4
            y = sy(value)
            svg.add(f'<line x1="{margin["l"]}" y1="{y:.1f}" x2="{width - margin["r"]}" y2="{y:.1f}" stroke="{GRID}"/>')
            svg.add(f'<text class="axis" x="{margin["l"] - 10}" y="{y + 4:.1f}" text-anchor="end">{value:.0f}</text>')
        off_y = sy(offline_value)
        svg.add(f'<line x1="{margin["l"]}" y1="{off_y:.1f}" x2="{width - margin["r"]}" y2="{off_y:.1f}" stroke="#eda100" stroke-width="2" stroke-dasharray="6 6">'
                f'<title>Offline-Optimized reference: {offline_value:.1f} {unit}</title></line>')
        pts = [(sx(t), sy(v)) for t, v in points]
        svg.add(f'<path d="{points_to_path(pts)}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>')
        for x, y in pts[1:-1]:
            svg.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{color}" stroke="{SURFACE}" stroke-width="1.5"/>')
        svg.add(f'<text class="axis" x="{width - margin["r"] - 4}" y="{off_y - 6:.1f}" text-anchor="end">Offline {offline_value:.1f} {unit}</text>')

    cir_axis_max = max(safe_max([v for _, v in cir_points] + [offline["cir"] / 1e6]), 1.0) * 1.15
    cbs_axis_max = max(safe_max([v for _, v in cbs_points] + [offline["cbs"] / 1e3]), 1.0) * 1.15
    panel(cir_points, margin["t"], "CIR (Mbps)", "Mbps", offline["cir"] / 1e6, "#2a78d6", cir_axis_max)
    panel(cbs_points, margin["t"] + panel_h + panel_gap, "CBS (Kbit)", "Kbit", offline["cbs"] / 1e3, "#1baf7a", cbs_axis_max)

    for tick in range(5):
        t = duration * tick / 4
        x = sx(t)
        svg.add(f'<text class="axis" x="{x:.1f}" y="{height - 34}" text-anchor="middle">{t:.1f}s</text>')
    svg.add('<text class="note" x="40" y="590">Preliminary PoC: dashed line is the current grid-selected static reference; solid lines are the online trajectory.</text>')
    return write_svg(f"cir_cbs_trajectory_{profile}.svg", svg)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate preliminary ATS PoC SVG figures")
    parser.add_argument("--deadline-profile", choices=["strict", "relaxed"], default="relaxed")
    parser.add_argument("--all-profiles", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    profiles = ["relaxed", "strict"] if args.all_profiles else [args.deadline_profile]
    paths = []
    for profile in profiles:
        data = load_compare(profile)
        paths.append(plot_metrics_bar(data, profile))
        paths.append(plot_delay_timeseries(data, profile))
        paths.append(plot_rule_timeline(data, profile))
        paths.append(plot_cir_cbs_trajectory(data, profile))
    print("Generated figures:")
    for path in paths:
        print(f"  {path}")


if __name__ == "__main__":
    main()
