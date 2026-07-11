# 文献阅读笔记（PDF 第一轮）

> 来源文件夹：`/Users/anshizhao/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wxid_gskyl58xstkt22_87c9/msg/file/2026-07`
> 日期：2026-07-08
> 说明：本轮为第一轮阅读，已完成 PDF 文本提取与重点内容梳理。部分论文需要后续精读公式、实验参数和引用文献。

---

## 0. 已读取 PDF 清单

1. `Efficient adaptive bandwidth allocation for deadline-aware online admission.pdf`
2. `Scheduling Real-Time Communication in IEEE 802.1Qbv.pdf`
3. `工业5G-TSN融合网络的异构流量整形器设计.pdf`
4. `CyclicSim  Comprehensive Evaluation of Cyclic Shapers in TSN.pdf`
5. `The Improvement of Scheduling Algorithm Based on Token Bucket and Weighted.pdf`
6. `Asynchronous Traffic Shaping and Redundancy Avoiding Unbounded Latencies.pdf`
7. `A Study on Optimal Ethernet-based Industrial Networks Construction Using Asynchronous Traffic Shaping.pdf`

全文文本已提取到：`ats-sim/literature/text/`

---

# 1. A Study on Optimal Ethernet-based Industrial Networks Construction Using Asynchronous Traffic Shaping in IEEE 802.1TSN and Downhill Simplex Method

**作者**：Akari Yoshimura, Yoshihiro Ito  
**会议**：ICOIN 2025  
**DOI**：10.1109/ICOIN63865.2025.10992702

## 核心内容

该文直接研究 ATS 在以太网工业网络中的参数优化问题。作者使用 **Downhill Simplex Method / Nelder-Mead 单纯形法** 搜索 ATS 参数，使工业网络中不同流量满足端到端时延要求。

文中明确 ATS 参数包括：

- **MRT**：Max Residence Time，最大驻留时间；
- **CIR**：Committed Information Rate，令牌产生速率；
- **CBS**：Committed Burst Size，令牌桶容量。

这篇论文和本课题关系最直接。

## 实验设置

- 仿真平台：OMNeT++ 6.0.1 + INET 4.5；
- 网络场景：简单实际工厂网络；
- 链路：100BASE-TX；
- 设备：6 个收发设备，9 个发送设备，1 个 RD，6 个交换机；
- 流量总数：33 条；
- 有要求的流量：27 条。

论文中的流量参数表：

| 设备 | 发送间隔 | 大小 | 优先级 | 时延要求 |
|---|---:|---:|---:|---:|
| HA0, HA1, HA2 | 500 μs | 150 B | 7 | 350 μs |
| HB0, HB1, HB2 | 500 μs | 150 B | 7 | 350 μs |
| SA0, SA1, SA2 | 1000 μs | 750 B | 6 | 600 μs |
| SB0-SB5 | 280-520 μs | 500 B | 5 | NA |

## 评价函数

论文定义评价函数，使未满足时延要求的流量产生惩罚。若所有流量满足需求，则评价值趋近 0。

## 结论

- 单纯形法有时能找到满足所有要求的 ATS 参数；
- 但对初始值敏感，可能陷入局部最优；
- 作者未来工作是寻找更合适的初始值，并在其他工业网络上评估。

## 对本课题的作用

**必须作为直接基线。**

建议命名为：

> Static-Optimized ATS / Offline Simplex ATS

本课题区别：

| 该文 | 本课题 |
|---|---|
| 离线优化 ATS 参数 | 在线自适应调整 ATS 参数 |
| 依赖多次仿真和初始值 | 运行时根据状态反馈调整 |
| 适合稳定网络 | 目标是动态 IIoT 场景 |
| 优化 MRT/CIR/CBS | 短期重点优化 CIR/CBS，MRT 可后续加入 |

## 下一步使用方式

1. 将本论文中的流量参数作为本仿真的重要参考；
2. 实现一个简化版离线网格搜索 / 单纯形基线；
3. 后续论文相关工作中重点对比。

---

# 2. Efficient Adaptive Bandwidth Allocation for Deadline-Aware Online Admission Control in Centralized Time-Sensitive Networking

**作者**：Sifan Yu, Feng He, Anlan Xie, Luxi Zhao  
**期刊**：Journal of Systems Architecture, 2025

## 核心内容

该文研究集中式 TSN 中针对事件触发 ET 流的在线准入控制和自适应带宽分配问题，基于 **TSN/ATS+CBS 架构**，用网络微积分计算时延界，动态分配和回收带宽。

## 关键贡献

- 面向动态实时应用；
- 在线准入控制；
- 动态带宽分配与回收；
- 基于网络微积分保证时延；
- 目标是提高可接纳流数量并降低接纳计算时间。

论文结论中给出的结果：

- 平均增加 **56%** admitted flows；
- 平均减少 **92%** admission time；
- 推迟瓶颈端口出现和首次拒绝请求。

## 与本课题关系

这是当前和本课题最接近的“动态 + TSN/ATS”工作。

但它的切入点不同：

| 该文 | 本课题 |
|---|---|
| 在线准入控制 | 在线 ATS 参数自适应 |
| 动态分配带宽 | 动态调整 CIR/CBS 等整形参数 |
| 面向 ET 流准入 | 面向动态工业流量整形 |
| 集中式控制器 | 目标是轻量规则，可解释、低开销 |

## 对本课题启发

1. 可借鉴其“动态场景下在线决策”的问题动机；
2. 可借鉴网络微积分作为时延保证工具；
3. 相关工作中必须说明与其区别；
4. 可作为对照：本课题不是 admission control，而是 shaping parameter adaptation。

---

# 3. Asynchronous Traffic Shaping and Redundancy: Avoiding Unbounded Latencies in In-Car Networks

**作者**：Teresa Lübeck, Philipp Meyer, Timo Häckel, Franz Korf, Thomas C. Schmidt  
**会议**：IEEE VNC 2025

## 核心内容

该文研究 ATS 与 FRER 冗余机制组合时可能产生的无界延迟问题。核心原因是 FRER 可能导致非 FIFO 行为，而 ATS 在非 FIFO 网络中可能累积延迟。

## 关键 ATS 机制描述

论文对 ATS 的解释非常有用：

- ATS 是 per-stream shaping；
- 使用 token bucket；
- 每个 incoming frame 会被计算 eligibility time；
- CIR 表示 token recovery rate；
- CBS 表示 bucket 最大 token 数；
- MRT 表示最大 residence time；
- 若 eligibility time 超过 arrival time + MRT，则帧会被丢弃；
- scheduler group 中 group eligibility time 用于保持同组帧顺序。

## 结论与方法

该文提出通过 ATS 调度器放置和参数配置，避免无界延迟条件。仿真实验验证了其配置方法可以避免无界延迟。

## 与本课题关系

该文不是做参数在线优化，而是分析 ATS 参数/放置对可界延迟的影响。

对本课题有两个作用：

1. **证明 ATS 参数配置非常关键**；
2. **提醒我们不能只考虑 CIR/CBS，MRT 也可能是重要参数**。

## 本课题应如何引用

相关工作中归入：

> ATS 机制安全性 / 时延有界性分析

可表述为：

> Lübeck 等指出 ATS 在非 FIFO 或冗余场景中存在无界延迟风险，并通过配置和放置策略恢复有界性。这说明 ATS 的配置对确定性性能具有关键影响，但该工作关注的是冗余/非 FIFO 场景下的有界性保证，而非动态 IIoT 场景中基于运行状态的在线参数自适应。

---

# 4. 工业5G-TSN融合网络的异构流量整形器设计

**作者**：李琳，骆亮生，许驰  
**单位**：中国科学院沈阳自动化研究所等  
**期刊**：计算机应用研究，2025  
**DOI**：10.19734/j.issn.1001-3695.2024.08.0268

## 核心内容

该文面向工业 5G-TSN 融合网络，提出异构流量整形器 HTS，用于同时处理控制任务、音视频任务、感知任务等多类型流量。

HTS 采用多种机制组合：

- 周期控制任务：单独划分队列，设置专属时隙，FIFO 整形；
- 非周期音视频/感知任务：共享流队列，信用值规则整形；
- 剩余非周期感知任务：令牌桶机制整形。

## 实验结果

OMNeT++ 仿真结果表明：

- HTS 可满足关键控制任务确定性传输要求；
- 支持音视频和感知任务共存；
- 将非共存传输任务最大端到端时延降低 87.29% 以上。

## 与本课题关系

这是“混合整形/异构整形”方向文献。

| 该文 | 本课题 |
|---|---|
| 设计 HTS 架构，组合 TAS/CBS/令牌桶等机制 | 聚焦 ATS 参数自适应 |
| 面向 5G-TSN 融合与多类型任务 | 面向动态 IIoT 中 ATS 参数变化 |
| 主要是机制组合 | 主要是在线参数优化 |
| OMNeT++ 验证 | 短期 Python 原型，中期后 OMNeT++ |

## 对本课题启发

1. 可借鉴其工业场景描述：控制任务、音视频任务、感知任务；
2. 可借鉴其混合流量分类方式；
3. 可用于说明“已有混合整形方案仍需复杂配置，动态参数自适应仍有空间”。

---

# 5. CyclicSim: Comprehensive Evaluation of Cyclic Shapers in Time-Sensitive Networking

**作者**：Rubi Debnath, Luxi Zhao, Mohammadreza Barzegaran, Sebastian Steinhorst  
**会议**：IEEE CCNC 2025 / arXiv 2024

## 核心内容

该文提出 CyclicSim，一个基于 OMNeT++ 和 INET 4.4 的开源仿真框架，用于评估 CQF、CSQF、MCQF 等 cyclic shapers。

虽然重点不是 ATS，但论文提到 TAS、ATS、CBS、SP 等机制已被广泛研究，CyclicSim 主要补 cyclic shaper 的评测空白。

## 贡献

- 提供开源 OMNeT++/INET4.4 框架；
- 支持多种 cyclic shaper；
- 在 synthetic 和 realistic network 上评估；
- 可作为 TSN 仿真基准。

## 与本课题关系

本课题短期不直接用 CyclicSim，但中期后可用于：

1. 迁移到 OMNeT++/INET；
2. 对比不同 shaping 机制；
3. 参考其仿真组织、参数设置、结果图表。

## 下一步使用方式

- 暂时不作为核心算法文献；
- 中期后作为仿真平台候选；
- 当前用于支撑“后续将迁移至 OMNeT++/INET”这一计划。

---

# 6. Scheduling Real-Time Communication in IEEE 802.1Qbv Time Sensitive Networks

**作者**：Silviu S. Craciunas, Ramon Serna Oliver, Martin Chmelík, Wilfried Steiner  
**会议**：RTNS 2016

## 核心内容

该文研究 IEEE 802.1Qbv TAS 的离线调度问题，使用 SMT 建模并计算多跳 TSN 网络中的确定性静态调度。

## 与本课题关系

它不是 ATS 文献，但可以用于：

1. 说明 TAS 的确定性优势与静态复杂性；
2. 支撑“静态调度/时间感知整形器难以适应动态流量”的背景；
3. 提供 TSN 周期性控制流建模的经典依据。

## 可引用点

- TSN 是工业与汽车实时以太网的重要方向；
- Qbv/TAS 可通过离线调度保证低抖动和确定性时延；
- 但其计算复杂、依赖预先已知流量和静态计划，不适合动态变化场景。

## 对本课题作用

作为背景铺垫：

> TAS 强确定性但静态、复杂；ATS 更灵活但参数配置问题突出，因此需要 ATS 参数自适应。

---

# 7. The Improvement of Scheduling Algorithm Based on Token Bucket and Weighted Fair Queue

**作者**：Zaiqun Wu, Huanchang Qin, Xiaomei Song, Guangyan Fu, Jiangfeng Li  
**会议**：ICTech 2023

## 核心内容

该文提出一种基于令牌桶和 WFQ 的改进调度算法，通过调整队列长度权重，改善实时流的 QoS，降低时延、抖动和丢包率。

## 主要思想

- token bucket 用于流量控制与整形；
- WFQ 用于多队列公平调度；
- 传统 WFQ 权重固定，可能导致资源浪费或拥塞；
- 改进方法根据队列长度调整权重，保障实时流 QoS。

## 与本课题关系

这篇论文**不是 TSN/ATS 专门论文**，但对“轻量反馈式自适应”有启发意义。

| 该文 | 本课题 |
|---|---|
| token bucket + WFQ | ATS token bucket 参数自适应 |
| 调整队列权重 | 调整 CIR/CBS/MRT |
| 面向一般 QoS | 面向 TSN/IIoT 确定性时延 |
| 不是 ATS | ATS 专门化 |

## 对本课题启发

可作为方法论支撑：

> 队列状态可以作为轻量反馈信号，用于动态调整整形/调度参数。

但不能作为核心 TSN 相关工作。

---

# 8. 当前文献体系如何服务本课题

根据这些文献，本课题相关工作可以重组为四类：

## 8.1 静态确定性调度

代表：Craciunas et al. 2016, Qbv/TAS scheduling。

作用：说明 TAS 可以提供确定性，但需要离线调度和静态配置，不适合动态场景。

## 8.2 ATS 离线参数优化

代表：Yoshimura & Ito 2025。

作用：直接基线。说明 ATS 参数可以通过数值优化求得，但其方法是离线的、对初始值敏感，不解决动态变化。

## 8.3 ATS 机制与有界性分析

代表：Lübeck et al. 2025。

作用：说明 ATS 参数配置和部署位置会影响时延有界性，参数不是随便设的。

## 8.4 混合/异构整形

代表：李琳等 2025 HTS。

作用：说明已有工作通过混合机制处理多类型工业流，但配置复杂，仍缺少轻量在线自适应。

## 8.5 在线自适应带宽/准入控制

代表：Yu et al. 2025。

作用：说明 TSN 动态场景下在线自适应是趋势，但他们关注 admission control / bandwidth allocation，不是 ATS 参数调整。

## 8.6 轻量反馈式调度

代表：Wu et al. 2023 token bucket + WFQ。

作用：说明利用队列状态进行轻量反馈调参是可行思路，但需要迁移到 ATS/TSN 场景。

---

# 9. 对本课题方案的修正建议

基于文献，建议对方案做三处修正：

## 9.1 决策变量不应只写 r,b，建议扩展为 CIR/CBS/MRT

原方案写为：

- r：整形速率；
- b：突发容量。

文献表明 ATS 典型参数是：

- CIR；
- CBS；
- MRT。

短期代码仍可先做 CIR/CBS，因为更简单；但论文形式化文档中应把 MRT 纳入完整决策变量：

> x = (CIR, CBS, MRT)

然后说明：

> 本阶段为降低实现复杂度，先固定 MRT，仅对 CIR 与 CBS 进行自适应；中期后扩展 MRT。

## 9.2 基线必须包含 Yoshimura & Ito 的离线优化

不能只和“随便设的静态参数”比。至少要有：

1. Static-Low：低谷静态配置；
2. Static-High：高峰静态配置；
3. Offline-Optimized：参考 Yoshimura & Ito 的离线优化配置；
4. Rule-Based Adaptive：本文方法。

## 9.3 场景参数应更靠近 Yoshimura & Ito / HTS

当前自写仿真参数还比较手工，应逐步改成：

- 链路：100BASE-TX 或 1Gbps 两组；
- 控制流：500 μs / 150B / priority 7 / 350 μs 或放宽为 10ms；
- 周期流、突发流、背景流混合；
- 优先级与队列结构参考文献。

短期中期展示可以继续用简化参数，但正式报告应说明参数来源。

---

# 10. 下一步建议

## 必做 1：更新形式化建模

将决策变量从：

> x = (r,b)

改为：

> x = (CIR, CBS, MRT)

并说明短期实现只调整 CIR/CBS，MRT 固定。

## 必做 2：更新相关工作表

把文献分成六类，写入中期报告。

## 必做 3：修正仿真参数来源

从 Yoshimura & Ito、HTS、Craciunas 中抽取参数，建立一个 `traffic_literature.yaml`，不要只用手调参数。

## 必做 4：实现规则库前，先确定对比基线

建议基线为：

- Static-Low；
- Static-High；
- Offline-Optimized；
- Rule-Based Adaptive。

## 必做 5：实现规则库 M7

规则库输入：q、P95 delay、lambda、sigma、drop。  
规则库动作：调整 CIR/CBS，MRT 暂固定。

## 必做 6：实验必须标注 preliminary

所有 Python 数据都标记为：

> simplified single-hop Python simulation, preliminary validation.

---

# 11. 当前最推荐的工作顺序

1. 修改 `ats-formalization.md`：引入 CIR/CBS/MRT；
2. 修改 `ats-rulelib-and-schedule.md`：规则动作改成 CIR/CBS，MRT 固定；
3. 新建 `traffic_literature.yaml`：用文献参数构造实验；
4. 写 M7 规则库；
5. 跑 Static-Low / Static-High / Rule-Based；
6. 做图；
7. 再做 Offline-Optimized。
