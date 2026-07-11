"""M2 出口链路调度器。

ATS 整形后的 TT/ET 包与未经整形的 BE 包在此汇合, 按严格优先级 (SP) 竞争链路:
TT/ET (高优先级) > BE (低优先级)。

非抢占 SP: 当前包发完才选下一个最高优先级包。
"""
import simpy
from collections import deque
from typing import Callable, Optional
from .packet import Packet, TT, ET, BE


class EgressLink:
    def __init__(self, env: simpy.Environment, bandwidth: float,
                 propagation_delay: float,
                 on_send: Optional[Callable[[Packet], None]] = None):
        self.env = env
        self.bandwidth = bandwidth
        self.propagation_delay = propagation_delay
        self.on_send = on_send
        self.hi_q: deque[Packet] = deque()
        self.lo_q: deque[Packet] = deque()
        self.busy = False
        self._wake_event: Optional[simpy.Event] = None
        self._proc = env.process(self.run())

    def send(self, pkt: Packet):
        if pkt.ptype in (TT, ET):
            self.hi_q.append(pkt)
        else:
            self.lo_q.append(pkt)
        if not self.busy and self._wake_event is not None and not self._wake_event.triggered:
            self._wake_event.succeed()

    def run(self):
        while True:
            pkt = None
            if self.hi_q:
                pkt = self.hi_q.popleft()
            elif self.lo_q:
                pkt = self.lo_q.popleft()
            if pkt is None:
                self._wake_event = self.env.event()
                yield self._wake_event
                continue
            self.busy = True
            tx_delay = pkt.size / self.bandwidth
            yield self.env.timeout(tx_delay + self.propagation_delay)
            pkt.arrive_time = self.env.now
            if self.on_send:
                self.on_send(pkt)
            self.busy = False
