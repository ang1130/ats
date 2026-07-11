"""M6 状态监控器。

为规则库 (M7) 提供状态向量 s(t_k)。
Week1 用基础版: 队列长度、到达速率、时延 P95、丢包、令牌水位。
滑动窗口估计。
"""
import simpy
from collections import deque
from statistics import mean
from .packet import TT, ET, BE


class Monitor:
    def __init__(self, env: simpy.Environment, shaper, window: float = 0.5,
                 interval: float = 50e-3):
        self.env = env
        self.shaper = shaper
        self.window = window
        self.interval = interval
        self.recent_arrivals = deque()   # (time, size) 窗口内到达
        self.recent_delays = deque()     # (time, delay) 窗口内关键流(TT/ET)时延
        self.recent_drops = deque()      # (time,) 窗口内丢包时刻
        self.samples = []                # 采样历史 [(t, state_dict)]
        self.on_sample = None            # M7 注册的回调

    def record_arrival(self, size: float):
        self.recent_arrivals.append((self.env.now, size))

    def record_send(self, delay: float):
        self.recent_delays.append((self.env.now, delay))

    def record_drop(self, t: float):
        self.recent_drops.append(t)

    def _purge(self):
        cutoff = self.env.now - self.window
        while self.recent_arrivals and self.recent_arrivals[0][0] < cutoff:
            self.recent_arrivals.popleft()
        while self.recent_delays and self.recent_delays[0][0] < cutoff:
            self.recent_delays.popleft()
        while self.recent_drops and self.recent_drops[0] < cutoff:
            self.recent_drops.popleft()

    def sample(self) -> dict:
        self._purge()
        # 到达速率 = 窗口内总 bits / 窗口长度
        total_bits = sum(s for _, s in self.recent_arrivals)
        lam = total_bits / self.window if self.window > 0 else 0.0
        # 时延 P95
        delays = [d for _, d in self.recent_delays]
        d_obs = self._percentile(delays, 95) if delays else 0.0
        # 到达速率波动度 σ: 用窗口内分段速率方差近似
        sigma = self._volatility()
        state = {
            "t": self.env.now,
            "q": self.shaper.queue_length,
            "lambda": lam,
            "d_obs": d_obs,
            "sigma": sigma,
            "token_level": self.shaper.token_level,
            "drop_flag": len(self.recent_drops) > 0,
        }
        self.samples.append(state)
        return state

    def _percentile(self, data, p):
        if not data:
            return 0.0
        s = sorted(data)
        k = int(len(s) * p / 100)
        k = min(k, len(s) - 1)
        return s[k]

    def _volatility(self) -> float:
        """窗口内到达速率波动度: 把窗口分 5 段, 算各段速率方差。"""
        if not self.recent_arrivals:
            return 0.0
        n_seg = 5
        seg_len = self.window / n_seg
        base = self.env.now - self.window
        seg_rates = [0.0] * n_seg
        for t, s in self.recent_arrivals:
            idx = int((t - base) / seg_len) if seg_len > 0 else 0
            idx = min(idx, n_seg - 1)
            seg_rates[idx] += s
        seg_rates = [r / seg_len for r in seg_rates if seg_len > 0]
        if len(seg_rates) < 2:
            return 0.0
        m = mean(seg_rates)
        return sum((r - m) ** 2 for r in seg_rates) / len(seg_rates)

    def run(self):
        """周期采样进程。"""
        while True:
            yield self.env.timeout(self.interval)
            state = self.sample()
            if self.on_sample:
                self.on_sample(state)
