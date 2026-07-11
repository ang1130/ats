"""Week1 动态场景: 静态配置在阶跃+突发下的表现。

架构:
  TT/ET 流 -> ATS 整形器 -> EgressLink (高优先级) -> 接收端
  BE 流 -------------------> EgressLink (低优先级) -> 接收端

BE 突发挤压自身发送, 不影响 TT/ET; 当 TT/ET 超过 ATS 速率时才拥塞。
"""
import sys, os, re, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import simpy
from src.packet import Packet, Stats, TT, ET, BE
from src.ats_shaper import ATSShaper
from src.egress import EgressLink
from src.traffic import TTGenerator, BEGenerator, ETInjector
from src.monitor import Monitor


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
        return _walk(__import__("yaml").safe_load(f))


def run_dynamic(traffic_cfg, scenario_cfg, r, b, label="static-dynamic"):
    link = traffic_cfg["link"]
    ats_cfg = traffic_cfg["ats"]
    dl = traffic_cfg["deadline"]
    rng = random.Random(traffic_cfg["sim"]["seed"])

    env = simpy.Environment()
    stats = Stats()
    monitor = Monitor(env, None, window=0.5, interval=traffic_cfg["sim"]["monitor_interval"])

    # EgressLink: 接收整形后 TT/ET + 直送 BE, 按优先级发送
    def on_send(pkt):
        stats.record(pkt)
        monitor.record_send(pkt.arrive_time - pkt.gen_time)
    egress = EgressLink(env, link["bandwidth"], link["propagation_delay"], on_send=on_send)

    # ATS 整形器 (只服务 TT/ET), 释放后送 EgressLink
    shaper = ATSShaper(env, r, b, ats_cfg["max_queue_packets"],
                       on_release=egress.send,
                       on_drop=lambda p: (stats.record(p), monitor.record_drop(env.now)))
    monitor.shaper = shaper
    env.process(monitor.run())

    def send_tt_et(pkt):  # TT/ET 入 ATS
        stats.record_generated()
        monitor.record_arrival(pkt.size)
        shaper.receive(pkt)

    def send_be(pkt):     # BE 直送 EgressLink, 不经 ATS
        stats.record_generated()
        monitor.record_arrival(pkt.size)
        egress.send(pkt)

    # TT 流
    tt_gens = {}
    all_tt = {f["id"]: f for f in traffic_cfg["tt_flows"]}
    for fid in scenario_cfg["initial_tt_flows"]:
        f = all_tt[fid]
        g = TTGenerator(env, f["id"], f["period"], f["size_bytes"], dl["D_max"], send_tt_et)
        g.start(); tt_gens[fid] = g

    # BE 背景
    be = BEGenerator(env, traffic_cfg["be"]["rate"], traffic_cfg["be"]["size_bytes"], send_be, rng)
    be.start()

    et_inj = ETInjector(send_tt_et, dl["D_max"]); et_inj.set_env(env)

    def schedule_events():
        for ev in sorted(scenario_cfg["events"], key=lambda e: e["time"]):
            yield env.timeout(ev["time"] - env.now)
            if ev["type"] == "step" and ev["action"] == "add_tt_flows":
                for f in ev["params"]["flows"]:
                    g = TTGenerator(env, f["id"], f["period"], f["size_bytes"], dl["D_max"], send_tt_et)
                    g.start(); tt_gens[f["id"]] = g
                print(f"[t={env.now:.1f}s] 阶跃: +TT流 -> 共 {len(tt_gens)} 条")
            elif ev["type"] == "step" and ev["action"] == "remove_tt_flows":
                for fid in ev["params"]["flow_ids"]:
                    if fid in tt_gens: tt_gens[fid].stop(); del tt_gens[fid]
                print(f"[t={env.now:.1f}s] 阶跃: -TT流 -> 共 {len(tt_gens)} 条")
            elif ev["type"] == "burst":
                et_inj.inject_burst(ev["params"]["n_packets"], ev["params"]["size_bytes"],
                                    ev["params"]["spread"], rng)
                print(f"[t={env.now:.1f}s] 突发: +{ev['params']['n_packets']} ET包")
    env.process(schedule_events())

    env.run(until=scenario_cfg["duration"])

    delays = stats.delays
    tt_et = stats.per_type_delays[TT] + stats.per_type_delays[ET]
    def pct(d, p):
        if not d: return float("nan")
        s = sorted(d); return s[min(int(len(s)*p/100), len(s)-1)]
    return {
        "label": label, "r": r, "b": b,
        "n_gen": stats.n_generated, "n_drop": stats.n_dropped,
        "drop_rate": stats.n_dropped/max(stats.n_generated,1),
        "mean_ms": (sum(delays)/len(delays)*1e3) if delays else float("nan"),
        "p95_ms": pct(delays,95)*1e3 if delays else float("nan"),
        "p99_ms": pct(delays,99)*1e3 if delays else float("nan"),
        "tt_et_p95_ms": pct(tt_et,95)*1e3 if tt_et else float("nan"),
        "tt_et_p99_ms": pct(tt_et,99)*1e3 if tt_et else float("nan"),
        "violation_rate": stats.deadline_violations/max(stats.n_tt_et,1),
        "n_tt_et": stats.n_tt_et,
    }, monitor


def main():
    tc = load_cfg("config/traffic.yaml")
    sc = load_cfg("config/scenario.yaml")
    res, mon = run_dynamic(tc, sc, tc["ats"]["r_default"], tc["ats"]["b_default"])
    print("="*60)
    print(f"静态 r={res['r']/1e6:.0f}Mbps, b={res['b']/1e3:.0f}Kbit, {sc['duration']}s")
    print("="*60)
    print(f"生成/丢包:     {res['n_gen']} / {res['n_drop']} ({res['drop_rate']*100:.2f}%)")
    print(f"平均时延:      {res['mean_ms']:.3f} ms")
    print(f"P95/P99 时延:  {res['p95_ms']:.3f} / {res['p99_ms']:.3f} ms")
    print(f"TT+ET P95/P99: {res['tt_et_p95_ms']:.3f} / {res['tt_et_p99_ms']:.3f} ms")
    print(f"10ms 违约率:   {res['violation_rate']*100:.2f}%  (TT/ET {res['n_tt_et']} 包)")
    samples = mon.samples
    peak = max(samples, key=lambda s: s["d_obs"])
    print(f"\n峰值: t={peak['t']:.1f}s q={peak['q']} λ={peak['lambda']/1e6:.2f}Mbps "
          f"d95={peak['d_obs']*1e3:.3f}ms")
    import json
    os.makedirs("results", exist_ok=True)
    with open("results/week1_dynamic_samples.json","w") as f:
        json.dump([{**s} for s in samples], f, indent=2, default=str)


if __name__ == "__main__":
    main()
