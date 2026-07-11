"""基于文献参数的 Static-Low vs Rule-Based 初步对比。

数据性质：preliminary single-hop Python simulation。

用法：
    cd ats-sim
    .venv/bin/python experiments/run_rule_compare.py

输出：
    results/rule_compare_literature.json

说明：
- 使用 traffic_literature.yaml 和 scenario_literature.yaml。
- 将文献参数映射到当前 Python PoC 模型。
- Rule-Based 只调整 CIR/CBS，MRT 固定。
"""
import sys, os, re, json, random, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
import simpy
from src.packet import Packet, Stats, TT, ET, BE
from src.ats_shaper import ATSShaper
from src.egress import EgressLink
from src.traffic import TTGenerator, BEGenerator, ETInjector
from src.monitor import Monitor
from src.rule_engine import RuleEngine, RuleParams
from src.metrics import summarize


def _to_float(x):
    if isinstance(x, str) and re.fullmatch(r"[+-]?\d+(\.\d+)?[eE][+-]?\d+", x.strip()):
        return float(x)
    return x


def _walk(obj):
    if isinstance(obj, dict):
        return {k: _walk(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_walk(v) for v in obj]
    return _to_float(obj)


def load_cfg(path):
    with open(path) as f:
        return _walk(yaml.safe_load(f))


def build_flow_map(cfg):
    flows = {}
    for f in cfg["prototype_mapping"]["tt_flows_from_literature"]:
        flows[f["id"]] = f
    for f in cfg["prototype_mapping"]["medium_flows_as_tt_or_et"]:
        flows[f["id"]] = f
    return flows


def flow_deadline(flow: dict, deadline_default: float, deadline_profile: str) -> float:
    """根据 profile 决定包 deadline。

    strict: 使用文献给出的每流 deadline (350us/600us)，缺失则 fallback 到 D_max。
    relaxed: 所有关键流统一使用 deadline.D_max（当前为 10ms），用于观察规则趋势。
    """
    if deadline_profile == "strict":
        return flow.get("deadline") or deadline_default
    return deadline_default


def default_rule_params(ats: dict, deadline_default: float) -> RuleParams:
    """工程初值规则参数；后续由 M8/M9 标定替换。"""
    return RuleParams(
        d_max=deadline_default,
        warn_ratio=0.8,
        cooldown=0.05,
        cir_min=ats["cir_min"],
        cir_max=ats["cir_max"],
        cbs_min=ats["cbs_min"],
        cbs_max=ats["cbs_max"],
        q_hi=3,
        q_lo=0,
        lambda_delta_hi=0.5e6,
        sigma_hi=5e11,
        token_full=0.85,
        cir_up=4e6,
        cir_down=1e6,
        cbs_up=20e3,
        cbs_down=10e3,
        hold_after_expand=0.2,
        low_load_windows_for_down=8,
        steady_windows=12,
        return_ratio=0.2,
    )


def run_once(label: str, adaptive: bool, traffic_cfg: dict, scenario_cfg: dict,
             cir: float, cbs: float, deadline_profile: str, rule_params: RuleParams = None):
    env = simpy.Environment()
    rng = random.Random(42)
    stats = Stats()
    recv_bits = [0.0]

    link = traffic_cfg["link"]
    ats = traffic_cfg["ats"]
    deadline_default = traffic_cfg["deadline"]["D_max"]

    monitor = Monitor(env, None, window=0.05, interval=5e-3)

    def on_send(pkt: Packet):
        stats.record(pkt)
        recv_bits[0] += pkt.size
        # 规则库只监控关键流 TT/ET 时延，避免 BE 混入 d_obs 造成误判
        if pkt.ptype in (TT, ET):
            monitor.record_send(pkt.arrive_time - pkt.gen_time)

    egress = EgressLink(env, link["bandwidth"], link["propagation_delay"], on_send=on_send)

    shaper = ATSShaper(env, cir, cbs, ats["max_queue_packets"],
                       on_release=egress.send,
                       on_drop=lambda p: (stats.record(p), monitor.record_drop(env.now)))
    monitor.shaper = shaper

    rule_engine = None
    if adaptive:
        params = rule_params or default_rule_params(ats, deadline_default)
        rule_engine = RuleEngine(env, shaper, params, default_cir=cir, default_cbs=cbs)
        monitor.on_sample = rule_engine.on_sample

    env.process(monitor.run())

    def send_tt_et(pkt: Packet):
        stats.record_generated()
        monitor.record_arrival(pkt.size)
        shaper.receive(pkt)

    def send_be(pkt: Packet):
        stats.record_generated()
        monitor.record_arrival(pkt.size)
        egress.send(pkt)

    # TT / medium flows
    flow_map = build_flow_map(traffic_cfg)
    tt_gens = {}
    for fid in scenario_cfg["initial_tt_flows"]:
        f = flow_map[fid]
        g = TTGenerator(env, f["id"], f["period"], f["size_bytes"],
                        flow_deadline(f, deadline_default, deadline_profile), send_tt_et)
        g.start()
        tt_gens[fid] = g

    # BE background: 文献为 280-520us 随机间隔，此处用均值近似为泊松速率
    be_cfg = traffic_cfg["prototype_mapping"]["be_background"]
    mean_interval = (be_cfg["interval_min"] + be_cfg["interval_max"]) / 2
    be_rate = be_cfg["size_bytes"] * 8 / mean_interval
    BEGenerator(env, be_rate, be_cfg["size_bytes"], send_be, rng).start()

    et = ETInjector(send_tt_et, deadline_default)
    et.set_env(env)

    def schedule_events():
        for ev in sorted(scenario_cfg["events"], key=lambda e: e["time"]):
            yield env.timeout(ev["time"] - env.now)
            if ev["type"] == "step" and ev["action"] == "add_tt_flows":
                for f in ev["params"]["flows"]:
                    g = TTGenerator(env, f["id"], f["period"], f["size_bytes"],
                                    flow_deadline(f, deadline_default, deadline_profile), send_tt_et)
                    g.start()
                    tt_gens[f["id"]] = g
            elif ev["type"] == "step" and ev["action"] == "remove_tt_flows":
                for fid in ev["params"]["flow_ids"]:
                    if fid in tt_gens:
                        tt_gens[fid].stop()
                        del tt_gens[fid]
            elif ev["type"] == "burst":
                et.inject_burst(ev["params"]["n_packets"], ev["params"]["size_bytes"],
                                ev["params"].get("spread", 0.0), rng)
    env.process(schedule_events())

    env.run(until=scenario_cfg["duration"])

    rule_summary = rule_engine.summary() if rule_engine else None
    result = summarize(stats, recv_bits[0], scenario_cfg["duration"], label, shaper.r, shaper.b, rule_summary)
    result["initial_cir"] = cir
    result["initial_cbs"] = cbs
    result["monitor_samples"] = monitor.samples
    result["rule_logs"] = rule_engine.logs if rule_engine else []
    return result


def strip_large(result):
    """控制终端打印体积。"""
    r = dict(result)
    r.pop("monitor_samples", None)
    r.pop("rule_logs", None)
    return r


def main():
    parser = argparse.ArgumentParser(description="Preliminary ATS rule-based comparison")
    parser.add_argument(
        "--deadline-profile",
        choices=["strict", "relaxed"],
        default="relaxed",
        help="strict 使用文献 350us/600us deadline；relaxed 统一使用 traffic_literature.yaml 中的 10ms D_max",
    )
    args = parser.parse_args()

    traffic_cfg = load_cfg("config/traffic_literature.yaml")
    scenario_cfg = load_cfg("config/scenario_literature.yaml")
    baselines = traffic_cfg["baselines"]

    static_low = baselines["static_low"]
    static_high = baselines["static_high"]

    results = []
    results.append(run_once("Static-Low", False, traffic_cfg, scenario_cfg,
                            static_low["cir"], static_low["cbs"], args.deadline_profile))
    results.append(run_once("Static-High", False, traffic_cfg, scenario_cfg,
                            static_high["cir"], static_high["cbs"], args.deadline_profile))
    results.append(run_once("Rule-Based", True, traffic_cfg, scenario_cfg,
                            static_low["cir"], static_low["cbs"], args.deadline_profile))

    os.makedirs("results", exist_ok=True)
    out = {
        "note": "Preliminary single-hop Python simulation. Rule thresholds are engineering defaults, not calibrated.",
        "deadline_profile": args.deadline_profile,
        "results": results,
    }
    out_path = f"results/rule_compare_literature_{args.deadline_profile}.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)

    print("=" * 72)
    print("Preliminary Static-Low / Static-High / Rule-Based comparison")
    print("配置：traffic_literature.yaml + scenario_literature.yaml")
    print(f"deadline profile: {args.deadline_profile}")
    print("注意：规则阈值尚未离线标定，结果仅为 PoC")
    print("=" * 72)
    for r in results:
        print(f"\n[{r['label']}]")
        print(f"  initial CIR/CBS: {r['initial_cir']/1e6:.1f} Mbps / {r['initial_cbs']/1e3:.1f} Kbit")
        print(f"  final   CIR/CBS: {r['cir']/1e6:.1f} Mbps / {r['cbs']/1e3:.1f} Kbit")
        print(f"  generated/drop:  {r['n_generated']} / {r['n_dropped']} ({r['drop_rate']*100:.2f}%)")
        print(f"  TT/ET P95/P99:   {r['tt_et_p95_delay_ms']:.3f} / {r['tt_et_p99_delay_ms']:.3f} ms")
        print(f"  violation rate:  {r['deadline_violation_rate']*100:.2f}% ({r['deadline_violations']}/{r['n_tt_et']})")
        if r["rule_summary"]:
            print(f"  rule adjustments: {r['rule_summary']['n_adjustments']} {r['rule_summary']['rule_counts']}")
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
