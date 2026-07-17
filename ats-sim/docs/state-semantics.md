# Python/SimPy PoC：状态与指标语义

本文件描述当前执行代码的实际语义，不将这些近似状态误写为完整 IEEE 802.1Qcr ATS 的标准状态。

## 控制状态

`Monitor` 在 `run_rule_compare.py` 中以 **50 ms window、5 ms interval** 采样，并将状态传给 `RuleEngine`。

| 状态 | 当前计算方式 | 使用边界 |
|---|---|---|
| `q` | `ATSShaper.queue_length`，即 TT/ET shaper FIFO 中的包数 | 不包含 `EgressLink` 中等待的包，也不包含 BE 竞争队列 |
| `lambda` | 最近 50 ms 内所有记录到达 bit / window | `send_tt_et` 和 `send_be` 均调用 `record_arrival`，故包含 TT、ET、BE |
| `d_obs` | 最近窗口内**成功发送** TT/ET 包 E2E delay 的 P95 | 不是队列驻留时间，也不是标准 ATS eligibility/residence measurement；窗口内没有成功关键包时为 0 |
| `sigma` | 将窗口分为 5 段，计算每段到达速率的总体方差 | 是到达波动的工程近似，不是标准化 burstiness 指标 |
| `drop_flag` | 最近窗口内发生至少一次 `ATSShaper` queue overflow drop | 不包括链路侧丢弃；当前没有 MRT drop 机制 |
| `token_level` | `_tokens_at(now) / CBS` | 虚拟 release 排程的归一化令牌盈余/缺口近似，可为负 |

## `token_level` 为什么可以为负

`ATSShaper` 在包到达时会为该包及 backlog 预约未来 release time，并提前推进其虚拟 token 状态。若在当前时刻观察该未来计划，`_tokens_at(now)` 可能为负值。

因此，当前 `token_level`：

- **不是**始终落在 `[0, 1]` 的物理 token fill ratio；
- 负值表示按当前预约释放计划存在令牌缺口/债务近似；
- 可被规则用于判断资源紧张，但不应被表述为标准 ATS meter 的物理桶水位；
- R4 仅在 token 较高、队列较低、观测时延较低时考虑回收 CIR，且受连续窗口与扩容后 hold period 约束。

## 在线 CIR/CBS 更新语义

`ATSShaper.set_params(new_cir, new_cbs)` 的行为：

1. 若无 backlog，先结算到当前时刻，再修改 CIR/CBS，并将 token 截断到新 CBS。
2. 若有 backlog，旧 release event 失效；从当前时刻开始，以新 CIR/CBS 对所有尚未释放的包重新安排 release time。
3. backlog 重排时虚拟 token 状态重置为 0，随后按 FIFO 重新预约。

这是为了让 Rule-Based 的扩容能立即影响 backlog 的工程近似；它不是完整 Eligibility-Time 状态机对既有 tag 和 per-hop residence state 的标准语义。

## 结果指标与分母

| 指标 | 当前分子 | 当前分母 | 注意事项 |
|---|---|---|---|
| `drop_rate` | 所有被 `ATSShaper` 溢出丢弃的包 | 所有生成包（TT/ET/BE） | 不是 MRT drop rate；当前没有 MRT drop |
| `deadline_violation_rate` | 成功接收 TT/ET 包中 `arrival_time > deadline` 的数量 | 成功接收的 TT/ET 包 `n_tt_et` | 不把 dropped packet 计为 deadline violation，故必须与 `drop_rate` 一起报告 |
| TT/ET P95/P99 | 成功接收 TT/ET 包的 E2E delay | 成功接收 TT/ET 包样本 | 不表示标准 ATS residence time |
| throughput | 已成功发送到接收端的 bit | 仿真时长 | 包含所有成功发送流量 |

## 与理论模型和后续 INET 的关系

理论状态向量仍可写为：

\[
s(t) = (q, \lambda, d_{obs}, \sigma, token, drop)
\]

但在当前 PoC 中，各项是实现导向的近似量。后续迁移至 OMNeT++/INET 时，应重新以原生 queue signal、ingress arrival signal、E2E/residence-time signal、Eligibility-Time meter 状态和明确的 drop reason 定义对应状态；不能假定本文件中的近似语义可直接等价迁移。
