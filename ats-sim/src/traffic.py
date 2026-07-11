"""M4 流量生成器 (TT / ET / BE)。

TT: 周期性产生 (Craciunas et al., EMSOFT 2016)
ET: 事件驱动, 由 M5 动态事件注入时调用 inject_burst
BE: 泊松到达 (背景流量)

参数依据见 docs/ats-references.md。
"""
import simpy
import random
from typing import Callable, Optional
from .packet import Packet, TT, ET, BE


class TTGenerator:
    """周期控制流生成器。一条 TT 流一个实例, 可动态启停 (阶跃事件)。"""

    def __init__(self, env: simpy.Environment, flow_id: int, period: float,
                 size_bytes: int, deadline: float, send_fn: Callable[[Packet], None]):
        self.env = env
        self.flow_id = flow_id
        self.period = period
        self.size = size_bytes * 8  # bytes -> bits
        self.deadline = deadline
        self.send_fn = send_fn
        self.active = False
        self._proc: Optional[simpy.Process] = None

    def start(self):
        if self.active:
            return
        self.active = True
        self._proc = self.env.process(self._run())

    def stop(self):
        self.active = False
        if self._proc is not None and self._proc.is_alive:
            self._proc.interrupt()

    def _run(self):
        try:
            while self.active:
                pkt = Packet(self.flow_id, TT, self.size, self.env.now, self.deadline)
                self.send_fn(pkt)
                yield self.env.timeout(self.period)
        except simpy.Interrupt:
            return


class BEGenerator:
    """尽力而为流, 泊松到达。"""

    def __init__(self, env: simpy.Environment, rate: float, size_bytes: int,
                 send_fn: Callable[[Packet], None], rng: random.Random):
        self.env = env
        self.rate = rate            # 平均到达速率 bits/s
        self.size = size_bytes * 8
        self.send_fn = send_fn
        self.rng = rng
        self.active = False

    def start(self):
        self.active = True
        self.env.process(self._run())

    def stop(self):
        self.active = False

    def _run(self):
        while self.active:
            # 指数间隔实现泊松到达: mean_interval = size / rate
            mean_interval = self.size / self.rate if self.rate > 0 else 1.0
            yield self.env.timeout(self.rng.expovariate(1.0 / mean_interval))
            pkt = Packet(-1, BE, self.size, self.env.now, None)
            self.send_fn(pkt)


class ETInjector:
    """事件触发流: 不周期生成, 由 M5 调用 inject_burst 注入突发。"""

    def __init__(self, send_fn: Callable[[Packet], None], deadline: float):
        self.send_fn = send_fn
        self.deadline = deadline
        self.env: Optional[simpy.Environment] = None

    def set_env(self, env: simpy.Environment):
        self.env = env

    def inject_burst(self, n_packets: int, size_bytes: int, spread: float,
                     rng: random.Random):
        """在 spread 秒内注入 n_packets 个 ET 包。"""
        if self.env is None:
            return
        for _ in range(n_packets):
            # 每个包在 [0, spread] 内随机偏移到达
            delay = rng.uniform(0, spread) if spread > 0 else 0
            self.env.process(self._send_one(delay, size_bytes))

    def _send_one(self, delay: float, size_bytes: int):
        yield self.env.timeout(delay)
        pkt = Packet(-2, ET, size_bytes * 8, self.env.now, self.deadline)
        self.send_fn(pkt)
