"""M7 自适应规则库引擎。

当前阶段：理论变量为 (CIR, CBS, MRT)，代码只在线调整 CIR/CBS，MRT 固定。

输入：Monitor.sample() 产生的状态 s：
  q, lambda, d_obs, sigma, token_level, drop_flag

输出：调用 ATSShaper.set_params(new_cir, new_cbs)，并记录规则触发日志。

注意：这是 proof-of-concept 规则库，阈值仍是工程初值；后续 M8 离线标定会替换这些阈值。
"""
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List


@dataclass
class RuleParams:
    # 时间与红线
    d_max: float = 10e-3
    warn_ratio: float = 0.8
    cooldown: float = 0.3

    # CIR/CBS 可行域
    cir_min: float = 1e6
    cir_max: float = 100e6
    cbs_min: float = 1e3
    cbs_max: float = 1e6

    # 阈值
    q_hi: int = 10
    q_lo: int = 1
    lambda_delta_hi: float = 1e6
    sigma_hi: float = 1e13
    token_full: float = 0.9
    token_empty: float = 0.1

    # 调整步长
    cir_up: float = 4e6
    cir_down: float = 1e6
    cbs_up: float = 20e3
    cbs_down: float = 10e3

    # 防抖：单次最大调整
    cir_delta_max: float = 8e6
    cbs_delta_max: float = 50e3

    # R4 降速迟滞：避免高峰期刚扩容就过早降速
    hold_after_expand: float = 0.2
    low_load_windows_for_down: int = 8

    # 稳态回归
    steady_windows: int = 10
    return_ratio: float = 0.25


class RuleEngine:
    """事件触发 + 节流 + 防抖的规则引擎。"""

    def __init__(self, env, shaper, params: RuleParams,
                 default_cir: float, default_cbs: float,
                 name: str = "rule-based"):
        self.env = env
        self.shaper = shaper
        self.params = params
        self.default_cir = default_cir
        self.default_cbs = default_cbs
        self.name = name

        self.last_adjust_time = -1e18
        self.last_expand_time = -1e18
        self.prev_lambda: Optional[float] = None
        self.prev_q: Optional[int] = None
        self.no_trigger_windows = 0
        self.low_load_windows = 0
        self.logs: List[Dict[str, Any]] = []

    def on_sample(self, state: dict):
        """Monitor 每次采样后调用。"""
        now = state["t"]
        lam = state.get("lambda", 0.0)
        q = state.get("q", 0)
        prev_lam = self.prev_lambda if self.prev_lambda is not None else lam
        prev_q = self.prev_q if self.prev_q is not None else q
        delta_lam = lam - prev_lam
        delta_q = q - prev_q

        self.prev_lambda = lam
        self.prev_q = q

        # 节流期内不调整，但保留状态更新
        if now - self.last_adjust_time < self.params.cooldown:
            return

        rule_id, dc, db, reason = self._decide(state, delta_lam, delta_q)
        if rule_id is None:
            self.no_trigger_windows += 1
            if self.no_trigger_windows >= self.params.steady_windows:
                rule_id, dc, db, reason = self._return_to_default()
                if rule_id is None:
                    return
            else:
                return
        else:
            self.no_trigger_windows = 0

        self._apply(rule_id, dc, db, state, reason)

    def _decide(self, s: dict, delta_lam: float, delta_q: int):
        p = self.params
        q = s.get("q", 0)
        d_obs = s.get("d_obs", 0.0)
        sigma = s.get("sigma", 0.0)
        token = s.get("token_level", 0.0)
        drop = s.get("drop_flag", False)

        # R5: 丢包/丢弃，最高优先级
        if drop:
            return "R5_DROP", p.cir_up, p.cbs_up, "drop observed; urgent expansion"

        # R2: 时延逼近红线
        if d_obs > p.warn_ratio * p.d_max:
            # 若同时队列堆积或令牌低，CIR/CBS 都加；否则先加 CIR
            db = p.cbs_up if (q > p.q_hi or token < p.token_empty) else 0.0
            return "R2_DELAY_WARN", p.cir_up, db, "observed delay approaches deadline"

        # R3: 突发尖峰，优先加 CBS
        if sigma > p.sigma_hi and delta_q > 0:
            return "R3_BURST", 0.0, p.cbs_up, "traffic burst detected"

        # R1: 队列堆积 + 到达速率上升
        if q > p.q_hi and delta_lam > p.lambda_delta_hi:
            return "R1_QUEUE_GROW", p.cir_up, 0.0, "queue growth with rising arrival rate"

        # R4: 资源过剩，降低 CIR。需要迟滞：
        # 1) 距离最近扩容超过 hold_after_expand；
        # 2) 连续多个采样窗口满足低负载条件；
        low_load = q <= p.q_lo and token > p.token_full and d_obs < 0.3 * p.d_max
        if low_load:
            self.low_load_windows += 1
        else:
            self.low_load_windows = 0
        if (
            low_load
            and self.low_load_windows >= p.low_load_windows_for_down
            and self.env.now - self.last_expand_time >= p.hold_after_expand
            and self.shaper.r > self.default_cir
        ):
            self.low_load_windows = 0
            return "R4_RESOURCE_EXCESS", -p.cir_down, 0.0, "sustained low load after hold period"

        return None, 0.0, 0.0, ""

    def _return_to_default(self):
        """R6: 稳态回归。"""
        p = self.params
        dc = (self.default_cir - self.shaper.r) * p.return_ratio
        db = (self.default_cbs - self.shaper.b) * p.return_ratio
        # 变化太小则不调
        if abs(dc) < 1e5 and abs(db) < 1e3:
            return None, 0.0, 0.0, ""
        return "R6_RETURN", dc, db, "steady state; return toward default"

    def _apply(self, rule_id: str, dc: float, db: float, state: dict, reason: str):
        p = self.params
        old_cir, old_cbs = self.shaper.r, self.shaper.b

        # 防抖截断
        dc = max(-p.cir_delta_max, min(p.cir_delta_max, dc))
        db = max(-p.cbs_delta_max, min(p.cbs_delta_max, db))

        new_cir = max(p.cir_min, min(p.cir_max, old_cir + dc))
        new_cbs = max(p.cbs_min, min(p.cbs_max, old_cbs + db))

        # 若无实际变化，不记录
        if abs(new_cir - old_cir) < 1e-9 and abs(new_cbs - old_cbs) < 1e-9:
            return

        self.shaper.set_params(new_cir, new_cbs)
        self.last_adjust_time = self.env.now
        if new_cir > old_cir or new_cbs > old_cbs:
            self.last_expand_time = self.env.now
        self.logs.append({
            "t": self.env.now,
            "rule": rule_id,
            "reason": reason,
            "old_cir": old_cir,
            "old_cbs": old_cbs,
            "new_cir": new_cir,
            "new_cbs": new_cbs,
            "dcir": new_cir - old_cir,
            "dcbs": new_cbs - old_cbs,
            "state": dict(state),
        })

    def summary(self) -> dict:
        counts: Dict[str, int] = {}
        for log in self.logs:
            counts[log["rule"]] = counts.get(log["rule"], 0) + 1
        return {
            "name": self.name,
            "n_adjustments": len(self.logs),
            "rule_counts": counts,
            "final_cir": self.shaper.r,
            "final_cbs": self.shaper.b,
            "params": asdict(self.params),
        }
