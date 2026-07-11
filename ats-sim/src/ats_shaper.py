"""M3 ATS 令牌桶整形器 (核心) —— 高效版 + 改参重调度。

职责: 对进入的 TT/ET 流做令牌桶整形, 决定每个包何时"释放"给出口链路。
整形后的包交给 EgressLink (M2) 传输, 不在此处理链路时延。
BE 流不经本整形器, 直接送 EgressLink。

当前阶段变量命名：
- r 等价于 ATS 参数 CIR (Committed Information Rate)
- b 等价于 ATS 参数 CBS (Committed Burst Size)
- MRT 在理论中保留，当前代码固定/未实现在线调整

单跳简化: 省略完整 ER 与标准 MRT 丢弃逻辑，中期后全栈仿真补完。

性能要点:
- 包到达时直接计算最早可释放时刻，O(1) 每包。
- set_params() 会对尚未释放的排队包重新计算释放时刻，使在线调参能立即影响 backlog。
"""
import simpy
from collections import deque
from typing import Optional, Callable
from .packet import Packet


class ATSShaper:
    def __init__(self, env: simpy.Environment, r: float, b: float,
                 max_queue_packets: int,
                 on_release: Optional[Callable[[Packet], None]] = None,
                 on_drop: Optional[Callable[[Packet], None]] = None):
        self.env = env
        self.r = r                  # CIR
        self.b = b                  # CBS
        self.tokens = b             # 初始满桶
        self.last_update = env.now
        self.max_queue_packets = max_queue_packets
        self.queue: deque[Packet] = deque()
        self.on_release = on_release
        self.on_drop = on_drop
        self._tail_release_time: float = env.now
        self._schedule_version = 0  # 改参重调度时用于忽略旧 release 事件

    def _tokens_at(self, t: float) -> float:
        return min(self.b, self.tokens + self.r * (t - self.last_update))

    def _plan_release_time(self, pkt: Packet, earliest: float) -> float:
        """基于当前虚拟令牌状态，计算 pkt 最早 release time，并推进虚拟令牌状态。"""
        t_avail = max(earliest, self._tail_release_time)
        tokens = self._tokens_at(t_avail)
        if tokens >= pkt.size:
            release_time = t_avail
        else:
            deficit = pkt.size - tokens
            release_time = t_avail + (deficit / self.r if self.r > 0 else 1.0)
        self.tokens = self._tokens_at(release_time) - pkt.size
        self.last_update = release_time
        self._tail_release_time = release_time
        return release_time

    def receive(self, pkt: Packet):
        pkt.enqueue_time = self.env.now
        if len(self.queue) >= self.max_queue_packets:
            pkt.dropped = True
            if self.on_drop:
                self.on_drop(pkt)
            return
        release_time = self._plan_release_time(pkt, self.env.now)
        self.queue.append(pkt)
        self.env.process(self._release(pkt, release_time, self._schedule_version))

    def _release(self, pkt: Packet, release_time: float, version: int):
        yield self.env.timeout(max(0.0, release_time - self.env.now))
        # 参数调整后旧 release 事件作废，避免重复释放
        if version != self._schedule_version:
            return
        # 释放时刻: 从队列移除，交给出口链路
        if self.queue and self.queue[0] is pkt:
            self.queue.popleft()
        else:
            # 理论上 FIFO 下不应发生；若发生，尽量移除该包避免重复滞留。
            try:
                self.queue.remove(pkt)
            except ValueError:
                pass
        pkt.dequeue_time = self.env.now
        if self.on_release:
            self.on_release(pkt)

    def set_params(self, r: float, b: float):
        """在线调整 CIR/CBS，并重调度 backlog。

        初版实现中，已排队包的 release_time 不会随新 CIR/CBS 改变，导致规则库提速无法
        立刻清理 backlog。本版在改参时作废旧 release 事件，并用新参数重新计算队列中
        尚未释放包的 release_time。
        """
        now = self.env.now
        backlog = list(self.queue)
        self._schedule_version += 1

        if backlog:
            # 队列已有积压时，旧虚拟令牌状态包含未来排队包的扣减；直接用新参数从 now 重新排。
            self.r = r
            self.b = b
            self.tokens = 0.0
            self.last_update = now
            self._tail_release_time = now
            for pkt in backlog:
                release_time = self._plan_release_time(pkt, now)
                self.env.process(self._release(pkt, release_time, self._schedule_version))
        else:
            # 无积压时，正常结算到当前时刻再改参。
            current_tokens = self._tokens_at(now)
            self.r = r
            self.b = b
            self.tokens = min(current_tokens, b)
            self.last_update = now
            self._tail_release_time = now

    @property
    def queue_length(self) -> int:
        return len(self.queue)

    @property
    def token_level(self) -> float:
        return self._tokens_at(self.env.now) / self.b if self.b > 0 else 0.0
