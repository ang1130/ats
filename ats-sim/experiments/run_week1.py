"""Week1 静态基线实验 (里程碑 M1)。

静态 ATS 配置 (r_default, b_default) 下, 稳态流量 (无动态事件), 输出基础指标。
架构与 run_week1_dynamic 一致: TT/ET->ATS->EgressLink, BE->EgressLink。
"""
import sys, os, re, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import simpy, yaml
from src.packet import Packet, Stats, TT, ET, BE
from src.ats_shaper import ATSShaper
from src.egress import EgressLink
from src.traffic import TTGenerator, BEGenerator
from src.monitor import Monitor


def _to_float(x):
    if isinstance(x, str) and re.fullmatch(r"[+-]?\d+(\.\d+)?[eE][+-]?\d+", x.strip()):
        return float(x)
    return x
def _walk(o):
    if isinstance(o, dict): return {k: _walk(v) for k, v in o.items()}
    if isinstance(o, list): return [_walk(v) for v in o]
    return _to_float(o)
def load_cfg(p):
    with open(p) as f: return _walk(yaml.safe_load(f))


def run_static(cfg_path="config/traffic.yaml", duration=None, label="static-default"):
    cfg = load_cfg(cfg_path)
    link, ats_cfg, dl, sim_cfg = cfg["link"], cfg["ats"], cfg["deadline"], cfg["sim"]
    rng = random.Random(sim_cfg["seed"])
    duration = duration or sim_cfg["duration"]
    env = simpy.Environment()
    stats = Stats()
    monitor = Monitor(env, None, window=0.5, interval=sim_cfg["monitor_interval"])
    recv_bits = [0.0]

    def on_send(pkt):
        stats.record(pkt); recv_bits[0] += pkt.size
        monitor.record_send(pkt.arrive_time - pkt.gen_time)
    egress = EgressLink(env, link["bandwidth"], link["propagation_delay"], on_send=on_send)
    shaper = ATSShaper(env, ats_cfg["r_default"], ats_cfg["b_default"],
                       ats_cfg["max_queue_packets"], on_release=egress.send,
                       on_drop=lambda p: (stats.record(p), monitor.record_drop(env.now)))
    monitor.shaper = shaper
    env.process(monitor.run())

    def send_tt_et(pkt):
        stats.record_generated(); monitor.record_arrival(pkt.size); shaper.receive(pkt)
    def send_be(pkt):
        stats.record_generated(); monitor.record_arrival(pkt.size); egress.send(pkt)

    for f in cfg["tt_flows"]:
        TTGenerator(env, f["id"], f["period"], f["size_bytes"], dl["D_max"], send_tt_et).start()
    BEGenerator(env, cfg["be"]["rate"], cfg["be"]["size_bytes"], send_be, rng).start()

    env.run(until=duration)
    delays = stats.delays
    tt_et = stats.per_type_delays[TT] + stats.per_type_delays[ET]
    def pct(d, p):
        if not d: return float("nan")
        s = sorted(d); return s[min(int(len(s)*p/100), len(s)-1)]
    return {
        "label": label, "duration": duration,
        "r": ats_cfg["r_default"], "b": ats_cfg["b_default"],
        "n_gen": stats.n_generated, "n_drop": stats.n_dropped,
        "drop_rate": stats.n_dropped/max(stats.n_generated,1),
        "mean_ms": (sum(delays)/len(delays)*1e3) if delays else float("nan"),
        "p95_ms": pct(delays,95)*1e3 if delays else float("nan"),
        "p99_ms": pct(delays,99)*1e3 if delays else float("nan"),
        "jitter_ms": (pct(delays,99)-pct(delays,1))*1e3 if delays else float("nan"),
        "tt_et_p95_ms": pct(tt_et,95)*1e3 if tt_et else float("nan"),
        "violation_rate": stats.deadline_violations/max(stats.n_tt_et,1),
        "throughput_mbps": recv_bits[0]/duration/1e6 if duration>0 else 0,
    }, monitor


def main():
    print("="*60); print("Week1 静态基线实验 (M1 里程碑)"); print("="*60)
    r, mon = run_static()
    print(f"\n配置: r={r['r']/1e6:.0f}Mbps, b={r['b']/1e3:.0f}Kbit, 时长={r['duration']}s")
    print(f"\n--- 聚合指标 ---")
    print(f"生成包数:       {r['n_gen']}")
    print(f"丢包率:         {r['drop_rate']*100:.2f}%")
    print(f"平均时延:       {r['mean_ms']:.3f} ms")
    print(f"P95/P99 时延:   {r['p95_ms']:.3f} / {r['p99_ms']:.3f} ms")
    print(f"抖动(P99-P1):   {r['jitter_ms']:.3f} ms")
    print(f"TT+ET P95:      {r['tt_et_p95_ms']:.3f} ms")
    print(f"10ms 违约率:    {r['violation_rate']*100:.2f}%")
    print(f"吞吐:           {r['throughput_mbps']:.2f} Mbps")
    print(f"\nWeek1 M1 完成 ✓ (稳态无压力, 指标作基线参考)")


if __name__ == "__main__":
    main()
