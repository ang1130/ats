"""公共数据类型。"""
from dataclasses import dataclass, field
from typing import Optional

# 流量类型
TT = "TT"  # 周期控制流
ET = "ET"  # 事件触发流
BE = "BE"  # 尽力而为流


@dataclass
class Packet:
    flow_id: int
    ptype: str            # TT / ET / BE
    size: float           # bits
    gen_time: float       # 生成时间 (s)
    deadline: Optional[float] = None  # TT/ET 的时延红线 (s), None 表示 BE 无红线

    # 运行时填充
    enqueue_time: Optional[float] = None   # 进入 ATS 队列时间
    dequeue_time: Optional[float] = None   # 离开 ATS 队列时间
    arrive_time: Optional[float] = None    # 到达接收端时间
    dropped: bool = False


@dataclass
class Stats:
    """单次仿真聚合统计。"""
    n_generated: int = 0
    n_dropped: int = 0
    delays: list = field(default_factory=list)        # E2E 时延 (s)
    per_type_delays: dict = field(default_factory=lambda: {TT: [], ET: [], BE: []})
    deadline_violations: int = 0                      # 超过 D_max 的包数 (TT/ET)
    n_tt_et: int = 0                                  # TT+ET 包数 (违约率分母)

    def record(self, pkt: Packet):
        if pkt.dropped:
            self.n_dropped += 1
            return
        delay = pkt.arrive_time - pkt.gen_time
        self.delays.append(delay)
        self.per_type_delays[pkt.ptype].append(delay)
        if pkt.deadline is not None:
            self.n_tt_et += 1
            if delay > pkt.deadline:
                self.deadline_violations += 1

    def record_generated(self):
        self.n_generated += 1
