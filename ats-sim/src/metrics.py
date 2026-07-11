"""M10 指标工具。"""
from .packet import TT, ET, BE


def percentile(data, p):
    if not data:
        return float("nan")
    s = sorted(data)
    return s[min(int(len(s) * p / 100), len(s) - 1)]


def summarize(stats, recv_bits: float, duration: float, label: str, cir: float, cbs: float,
              rule_summary=None):
    delays = stats.delays
    tt_et = stats.per_type_delays[TT] + stats.per_type_delays[ET]
    be = stats.per_type_delays[BE]
    return {
        "label": label,
        "duration": duration,
        "cir": cir,
        "cbs": cbs,
        "n_generated": stats.n_generated,
        "n_dropped": stats.n_dropped,
        "drop_rate": stats.n_dropped / max(stats.n_generated, 1),
        "mean_delay_ms": (sum(delays) / len(delays) * 1e3) if delays else float("nan"),
        "p95_delay_ms": percentile(delays, 95) * 1e3 if delays else float("nan"),
        "p99_delay_ms": percentile(delays, 99) * 1e3 if delays else float("nan"),
        "tt_et_mean_delay_ms": (sum(tt_et) / len(tt_et) * 1e3) if tt_et else float("nan"),
        "tt_et_p95_delay_ms": percentile(tt_et, 95) * 1e3 if tt_et else float("nan"),
        "tt_et_p99_delay_ms": percentile(tt_et, 99) * 1e3 if tt_et else float("nan"),
        "be_mean_delay_ms": (sum(be) / len(be) * 1e3) if be else float("nan"),
        "deadline_violation_rate": stats.deadline_violations / max(stats.n_tt_et, 1),
        "deadline_violations": stats.deadline_violations,
        "n_tt_et": stats.n_tt_et,
        "throughput_mbps": recv_bits / duration / 1e6 if duration > 0 else 0.0,
        "rule_summary": rule_summary,
    }
