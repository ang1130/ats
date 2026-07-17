# OMNeT++/INET ATS 调研记录

> 调研日期：2026-07-16  
> 范围：IEEE 802.1Qcr ATS、Eligibility Time、CIR/CBS/MRT 映射、最小 TSN 拓扑、状态反馈控制器迁移、版本与学习路径。  
> 边界：本记录仅基于官方文档、官方源码和可靠资料进行调研；未安装 OMNeT++/INET，未修改仿真代码。

---

## 1. 结论摘要

**INET 已提供官方 ATS / Eligibility-Time 实现，不需要从零实现仅基于令牌桶的 ATS 近似模块。**

推荐将正式实验平台定位为：

> 复用 INET 原生 Eligibility-Time ATS 数据平面，并把论文创新实现为一个自定义的在线状态反馈控制器，以及必要时对 meter 的小范围扩展。

具体分工：

- **复用 INET**：Eligibility Time 计算、MRT 过滤、Eligibility-Time 排队、eligibility gate、IEEE 802.1Q 集成。
- **自行实现**：动态 CIR/CBS/MRT 重配置语义、状态采集、R1–R6 规则库、R4 迟滞、Offline-Optimized 搜索、动态工业负载场景、统计与实验编排。
- **Python/SimPy PoC**：保留为问题定义、规则预标定与实验设计来源；不作为正式论文结果平台。

---

## 2. INET 对 ATS / IEEE 802.1Qcr 的支持

### 2.1 官方原生模块

| 目标能力 | INET 模块 | 支持结论 |
|---|---|---|
| IEEE 802.1Q 异步整形器 | `Ieee8021qAsynchronousShaper` | 直接支持 |
| Eligibility Time 计算 | `EligibilityTimeMeter` | 直接支持 |
| MRT 超限过滤/丢弃 | `EligibilityTimeFilter` | 直接支持 |
| 按 Eligibility Time 排队 | `EligibilityTimeQueue` | 直接支持 |
| 到 eligibility time 前阻止发送 | `EligibilityTimeGate` | 直接支持 |
| 组级 Eligibility Time 状态 | `GroupEligibilityTimeMeter`、`GroupEligibilityTimeTable` | 直接支持 |
| 802.1Q ingress filter 集成 | `ATSIeee8021qFilter` | 直接支持 |
| 通用、协议无关的整形组合 | `AsynchronousShaper` | 可复用 |

关键官方源码证据：

- [`Ieee8021qAsynchronousShaper.ned`](https://github.com/inet-framework/inet/blob/9097c7b3a64dd31cd807d3ce51707d4540f7a633/src/inet/linklayer/ieee8021q/Ieee8021qAsynchronousShaper.ned) 明确说明该模块实现 IEEE 802.1Q asynchronous shaper，且为 `EligibilityTimeGate` 的别名。
- [`ATSIeee8021qFilter.ned`](https://github.com/inet-framework/inet/blob/9097c7b3a64dd31cd807d3ce51707d4540f7a633/src/inet/linklayer/ieee8021q/ATSIeee8021qFilter.ned) 默认组合 `GroupEligibilityTimeMeter`、`EligibilityTimeFilter`、`GroupEligibilityTimeTable`。
- [`AsynchronousShaper.ned`](https://github.com/inet-framework/inet/blob/9097c7b3a64dd31cd807d3ce51707d4540f7a633/src/inet/queueing/shaper/AsynchronousShaper.ned) 默认采用 `EligibilityTimeQueue` 与 `EligibilityTimeGate`。

官方还提供以下可运行/可检查的 TSN 例程：

1. [Asynchronous Shaper showcase](https://github.com/inet-framework/inet/tree/9097c7b3a64dd31cd807d3ce51707d4540f7a633/showcases/tsn/trafficshaping/asynchronousshaper)
2. [CBS and ATS showcase](https://github.com/inet-framework/inet/tree/9097c7b3a64dd31cd807d3ce51707d4540f7a633/showcases/tsn/trafficshaping/cbsandats)

因此，后续工作不应将项目表述为“从零实现 ATS”；更准确的定位是：

> 采用 INET 提供的 Eligibility-Time ATS 建模组件作为基础数据平面；针对在线自适应控制所需的运行时重配置与状态导出能力进行扩展。

### 2.2 标准符合性表述边界

IEEE 官方页面说明，IEEE 802.1Qcr-2020 规定面向恒定速率全双工链路的异步流量整形：

- [IEEE 802.1Qcr 官方页面](https://1.ieee802.org/tsn/802-1qcr/)

INET ATS showcase 将 ATS 归因于 IEEE 802.1Qcr，并指出其不同于 time-aware shaper，不需要网络范围的协调时钟。

论文中建议避免未经逐条核验而声称“INET 完整实现 802.1Qcr 的全部语义”。建议使用以下严谨表述：

> INET 提供以 Eligibility Time Meter、Filter、Queue 和 Gate 为核心的 IEEE 802.1Q 异步整形建模组件，并提供官方 ATS showcase。本文以该实现为 ATS 仿真基础；对组级 eligibility 状态、逐跳驻留时间边界及在线重配置语义，通过源码核验与实验进一步确认。

---

## 3. CIR / CBS / MRT 映射

论文理论参数：

\[
x = (CIR, CBS, MRT)
\]

与 INET ATS 模块的直接映射：

| 论文概念 | INET 参数或机制 | 说明 |
|---|---|---|
| `CIR` | `committedInformationRate` | 承诺信息速率 |
| `CBS` | `committedBurstSize` | 承诺突发容量 |
| `MRT` | `maxResidenceTime` + `EligibilityTimeFilter` | 驻留超限后的过滤/丢弃约束 |
| Eligibility Time | `EligibilityTimeTag` | 包所携带的可发送资格时间 |
| 资格时间排序和释放 | `EligibilityTimeQueue` + `EligibilityTimeGate` | 未到资格时间不能发送 |

相关一手资料：

- [Asynchronous Shaper showcase 文档](https://github.com/inet-framework/inet/blob/9097c7b3a64dd31cd807d3ce51707d4540f7a633/showcases/tsn/trafficshaping/asynchronousshaper/doc/index.rst)
- [`EligibilityTimeMeter.cc`](https://github.com/inet-framework/inet/blob/9097c7b3a64dd31cd807d3ce51707d4540f7a633/src/inet/protocolelement/shaper/EligibilityTimeMeter.cc)
- [`EligibilityTimeFilter.cc`](https://github.com/inet-framework/inet/blob/9097c7b3a64dd31cd807d3ce51707d4540f7a633/src/inet/protocolelement/shaper/EligibilityTimeFilter.cc)
- [CBS + ATS showcase 配置](https://github.com/inet-framework/inet/blob/9097c7b3a64dd31cd807d3ce51707d4540f7a633/showcases/tsn/trafficshaping/cbsandats/omnetpp.ini)

### 不推荐作为主方案的通用令牌桶路径

`TokenBucketMeter` 可提供 CIR/CBS 风格的通用计量，但不应替代 ATS 的 Eligibility-Time 数据平面。它缺少：

- Eligibility Time 计算与标记；
- 按 Eligibility Time 排队；
- Eligibility gate 发放语义。

它仅适合充当普通令牌桶对照、近似机制或辅助实验组件。

来源：[`TokenBucketMeter.ned`](https://github.com/inet-framework/inet/blob/9097c7b3a64dd31cd807d3ce51707d4540f7a633/src/inet/queueing/meter/TokenBucketMeter.ned)。

---

## 4. 推荐的数据平面与控制平面架构

### 4.1 数据平面

```text
Ingress classification / stream identification
        │
        ▼
ATSIeee8021qFilter
  ├─ GroupEligibilityTimeMeter
  │      └─ CIR / CBS / MRT 受控参数
  ├─ EligibilityTimeFilter
  │      └─ MRT 超限过滤/丢弃
  └─ GroupEligibilityTimeTable
        │
        ▼
Egress queue
  ├─ EligibilityTimeQueue
  └─ Ieee8021qAsynchronousShaper
        │
        ▼
Ethernet link
```

### 4.2 控制平面

```text
AtsStateFeedbackController（自定义 cSimpleModule）
  │
  ├─ 周期采样 q, λ, d_obs, σ, token, drop
  ├─ 执行 R1–R6
  ├─ 处理 R4 迟滞、冷却时间和最小驻留时间
  ├─ 请求更新 CIR / CBS，后期可扩展 MRT
  └─ 输出规则触发日志、状态快照与参数轨迹
```

核心原则：不要重新实现完整 ATS 数据平面；论文方法的主要创新点应聚焦为“动态工业负载下的 ATS 参数在线反馈控制”。

---

## 5. 运行时 CIR/CBS/MRT 更新：待验证与建议扩展

现有官方 showcase 主要采用静态 `.ini` 配置。当前调研**未确认**以下参数是否有官方统一、可安全使用的运行时热更新接口：

- `committedInformationRate`
- `committedBurstSize`
- `maxResidenceTime`

即使 OMNeT++ 允许修改参数对象，模块也可能只在初始化时读取参数，或已经为排队报文计算了 Eligibility Time。因此不能仅依赖如下形式来定义论文控制方法：

```cpp
module->par("committedInformationRate").setDoubleValue(...);
```

### 推荐扩展

建议实现：

```text
AdaptiveEligibilityTimeMeter extends EligibilityTimeMeter
```

其提供显式控制接口，例如 `updateProfile(cir, cbs, mrt)`，并明确：

1. 新参数从何时开始对新到达包生效；
2. 队列中已带 `EligibilityTimeTag` 的报文是否保持旧标签；
3. meter 内部 token / eligibility 状态是保留、限幅还是重置；
4. MRT 更新后对已排队和新到达报文的语义；
5. 每次更新应记录的流 ID、规则 ID、旧/新参数和时间戳。

在线更新语义本身应成为方法定义的一部分，而不是隐含的实现细节。

---

## 6. 最小 TSN 拓扑与实验推进

### 6.1 Layer A：最小 ATS 验证拓扑

优先复用官方 `TsnLinearNetwork` 的单跳组织方式：

```text
Talker ── TSN Bridge/Switch ── Listener
              │
              ├─ ingress ATS meter/filter
              └─ egress eligibility-time queue/gate
```

官方 CBS+ATS showcase 的配置采用：

```ini
network = inet.networks.tsn.TsnLinearNetwork
```

来源：[官方 `cbsandats/omnetpp.ini`](https://github.com/inet-framework/inet/blob/9097c7b3a64dd31cd807d3ce51707d4540f7a633/showcases/tsn/trafficshaping/cbsandats/omnetpp.ini)。

初始建议流量：

| 流量 | 用途 |
|---|---|
| 1 条 ATS 受控流 | 验证 CIR/CBS/MRT 和 Eligibility-Time 行为 |
| 1 条 BE 背景流 | 提供竞争与排队压力 |
| 可选 1 条优先级竞争流或 CBS 流 | 复用 CBS+ATS 示例以增强竞争真实性 |

目标：先验证参数映射、tag/queue/gate 流水线与统计口径，再开始复杂工业场景。

### 6.2 Layer B：论文主实验单交换机拓扑

```text
Talker_1  ─┐
Talker_2  ─┼── TSN Switch ── Listener
Talker_3  ─┤
BE Source ─┘
```

建议含义：

| 流 | 作用 |
|---|---|
| High-priority periodic control | 周期控制类工业流 |
| Medium periodic flow | 常规监测或业务流 |
| BE background | 竞争负载 |
| ET burst | 告警、急停或异常状态上报 |

动态阶段：

```text
低负载 → 负载上升 → ET/告警突发 → 负载回落
```

该设计与现有迁移计划 [第 4 节](omnetpp-migration-plan.md#4-目标-omnet-最小拓扑) 一致。

---

## 7. Static-Low / Static-High / Offline-Optimized / Rule-Based

| 策略 | 参数配置 | 是否在线更新 | 角色 |
|---|---|---:|---|
| Static-Low | 固定低资源 CIR/CBS/MRT | 否 | 节约资源但在峰值下可能失效 |
| Static-High | 固定高资源 CIR/CBS/MRT | 否 | 性能强基线，但可能资源保守 |
| Offline-Optimized | 在相同 OMNeT++ 场景下网格搜索得到的固定参数 | 否 | 静态最优参考 |
| Rule-Based | 初值 + R1–R6 在线调节 | 是 | 论文提出方法 |

### 严格比较控制项

四组策略必须保持一致：

- 拓扑、链路速率、队列容量和优先级；
- 流量到达轨迹、突发发生时刻；
- 随机种子集合；
- 仿真时长与 warm-up 规则；
- deadline profile；
- 统计窗口、聚合方式和丢包分类。

### Python PoC 参数的使用边界

当前 Python PoC 下的 `Static-Low`、`Static-High` 与 `Offline-Optimized` 参数仅能作为 OMNeT++ 搜索范围和初始候选。正式的 Offline-Optimized 必须在相同的 OMNeT++ 拓扑、流量、链路和 MRT 语义下重新搜索。

---

## 8. R1–R6 控制器迁移

### 8.1 状态变量映射

| PoC 状态 | OMNeT++ 推荐来源 | 实现关注点 |
|---|---|---|
| `q` | `EligibilityTimeQueue` queue length / packet count | 使用 queue signal 或定期快照 |
| `λ` | ingress packet arrival 计数 | 滑动窗口：`arrivals / Δt` |
| `d_obs` | sink 端到端时延，或 switch residence / eligibility waiting time | 主决策指标建议使用 per-flow E2E delay |
| `σ` | 滑动窗口到达间隔或瞬时速率的方差 | 在论文中固定数学定义 |
| `token` | meter 内部 token / eligibility 状态 | 原生未必导出，建议扩展 signal |
| `drop` | filter、queue、sink 的丢弃信号 | 必须区分丢弃原因 |
| flow ID | stream identifier / VLAN PCP / application flow ID | 保持 per-flow 可追踪性 |

建议为突发强度固定可复现定义，例如：

\[
\sigma_t = \operatorname{CV}(\lambda_{t-W+1}, \ldots, \lambda_t)
\]

或：

\[
\sigma_t = \frac{\max(\lambda_{t-W+1}, \ldots, \lambda_t)}
{\operatorname{mean}(\lambda_{t-W+1}, \ldots, \lambda_t)+\epsilon}
\]

### 8.2 R1–R6 映射

| 规则 | 输入 | 动作 | 实现要点 |
|---|---|---|---|
| R1_QUEUE_GROW | `q↑`、`λ↑` | 增加 CIR | 过滤短窗口噪声 |
| R2_DELAY_WARN | `d_obs` 接近 deadline | 增加 CIR，必要时 CBS | 用相对 deadline 阈值 |
| R3_BURST | `σ↑` | 优先增加 CBS | 固定突发统计窗口 |
| R4_RESOURCE_EXCESS | 长期低 q、低 λ、低 delay | 逐步降低 CIR | 必须实施迟滞 |
| R5_DROP | MRT/filter/queue drop | 紧急扩容或保护状态 | 区分 drop 原因 |
| R6_RETURN | 稳态恢复 | 回到默认/经济配置 | 避免与 R4 振荡 |

### 8.3 R4 迟滞建议

R4 的“过早降速”问题应在 OMNeT++ 阶段正式建模为：

- 双阈值：`lowThreshold < highThreshold`；
- 连续满足低负载条件 `K` 个控制周期后，才允许降速；
- 每次降速后最小驻留时间 `T_hold`；
- CIR/CBS 每次调整均有有界步长；
- R2 或 R5 触发时，立即取消 R4 冷却或降速状态。

该迟滞机制可作为控制稳定性设计的一部分，而非经验补丁。

---

## 9. 正式实验指标

建议统一输出：

- deadline violation rate；
- drop rate，区分 MRT/filter drop、queue overflow 与其他原因；
- E2E delay：mean、P95、P99、max；
- jitter；
- queue length 与 queueing delay；
- eligibility waiting time；
- 吞吐率、有效负载交付率；
- CIR/CBS/MRT 参数轨迹；
- R1–R6 触发次数、触发持续时间和动作幅度；
- 资源使用代理指标，例如平均 CIR、峰值 CIR、CBS 配额。

---

## 10. 推荐版本与工程组织

### 10.1 版本组合

截至 2026-07-16，建议优先尝试：

| 组件 | 推荐版本 | 依据 |
|---|---|---|
| OMNeT++ | 6.4.0 | 当前正式发布版 |
| INET | 4.7.0 | 当前正式发布版；发布说明要求 OMNeT++ 6.4 或更高 |

来源：

- [OMNeT++ 6.4.0 release](https://github.com/omnetpp/omnetpp/releases/tag/omnetpp-6.4.0)
- [INET 4.7.0 release](https://github.com/inet-framework/inet/releases/tag/v4.7.0)

正式实验应锁定 release/tag；不要直接以不断变化的 `master` 作为论文数据平台。记录内容至少包括：OMNeT++、INET、commit hash、编译器、OS、随机种子和 NED path。

本次源码存在性核验所用的 INET 固定提交：

```text
9097c7b3a64dd31cd807d3ce51707d4540f7a633
```

它只作为本次调研证据锚点；最终实验应在锁定的版本中再次确认模块名、参数名和 showcase 可运行性。

### 10.2 建议目录布局

不建议将 OMNeT++ 或 INET 源码直接放进论文项目仓库。建议：

```text
~/opt/
  omnetpp-6.4/
  inet-4.7/

~/Desktop/ats/
  ats-sim/                  # 既有 Python PoC
  omnetpp-ats-study/        # 新建的正式仿真工程
    simulations/
    src/
    ned/
    results/
    scripts/
    docs/
```

这种布局可使 Python 原型、正式仿真工程与第三方依赖版本彼此独立。

---

## 11. 学习与实现顺序

### Phase 0：冻结环境、复现官方示例

1. 安装并构建 OMNeT++ 6.4.0 和 INET 4.7.0；
2. 运行普通 `TsnLinearNetwork`；
3. 运行 `asynchronousshaper` showcase；
4. 运行 `cbsandats` showcase；
5. 保存原始配置与结果，作为环境验收依据。

### Phase 1：理解 ATS 数据平面

建议按顺序阅读：

1. [`EligibilityTimeMeter.cc`](https://github.com/inet-framework/inet/blob/9097c7b3a64dd31cd807d3ce51707d4540f7a633/src/inet/protocolelement/shaper/EligibilityTimeMeter.cc)；
2. `EligibilityTimeTag`；
3. `EligibilityTimeFilter`；
4. `EligibilityTimeQueue`；
5. `EligibilityTimeGate`；
6. [`ATSIeee8021qFilter.ned`](https://github.com/inet-framework/inet/blob/9097c7b3a64dd31cd807d3ce51707d4540f7a633/src/inet/linklayer/ieee8021q/ATSIeee8021qFilter.ned)；
7. [`Ieee8021qAsynchronousShaper.ned`](https://github.com/inet-framework/inet/blob/9097c7b3a64dd31cd807d3ce51707d4540f7a633/src/inet/linklayer/ieee8021q/Ieee8021qAsynchronousShaper.ned)。

### Phase 2：静态 baseline

1. 建立单 ATS 流 + BE 流；
2. 复现 Static-Low / Static-High；
3. 在 OMNeT++ 中重跑 Offline-Optimized 网格搜索；
4. 验证 delay、drop、queue、throughput 统计；
5. 增加多条工业流与 burst。

### Phase 3：仅观测，不调参

实现 controller 的观测模式，输出 `q, λ, d_obs, σ, token, drop`，但不改变 CIR/CBS。先验证状态口径和趋势，再接入控制动作。

### Phase 4：接入动态控制

1. 实现 `AdaptiveEligibilityTimeMeter`；
2. 定义参数更新与内部状态的语义；
3. 接入 R1–R6；
4. 首先只调 CIR；
5. 再加入 CBS；
6. 最后单独研究 MRT，不建议初期三参数全闭环。

### Phase 5：论文级扩展验证

- 多随机种子；
- 多负载强度；
- 多 burst 模式；
- strict / relaxed deadline profiles；
- 参数敏感性；
- 从单跳再扩展到多跳；
- 统一报告置信区间。

---

## 12. 安装后优先二次核验项

1. INET 4.7.0 中是否保留相关模块名与参数名；
2. `committedInformationRate`、`committedBurstSize`、`maxResidenceTime` 的类型、单位、默认值和作用位置；
3. meter 是否可安全运行时重配置，或是否仅初始化阶段读取参数；
4. 参数更新后既有 `EligibilityTimeTag`、队列内报文和 meter 内部状态的语义；
5. `GroupEligibilityTimeMeter` 的 per-stream / per-group / per-hop 状态共享与重置规则；
6. queue、drop、packet delay 等可订阅 signal 的真实名称和统计含义；
7. 官方 `cbsandats` 示例中 stream classification、bridge port、queue 的实际连接；
8. 多跳时每跳 ATS ingress filter 与 egress eligibility queue/gate 的配置需求。

---

## 13. 可用于论文或中期材料的定位表述

> 本研究采用 INET 提供的 Eligibility-Time 异步流量整形组件构建 IEEE 802.1Q ATS 仿真基础。针对动态工业物联网负载下固定 CIR、CBS、MRT 配置易发生失配的问题，本文进一步设计基于队列长度、到达率、观测时延、突发强度、整形状态与丢包反馈的自适应参数控制方法。Python/SimPy 单跳原型仅用于问题验证、规则设计与参数预筛选；所有正式实验结论以 OMNeT++/INET 平台的可复现实验结果为准。

---

## 14. 参考资料

1. [IEEE 802.1Qcr 官方页面](https://1.ieee802.org/tsn/802-1qcr/)
2. [INET TSN Traffic Shaping showcase 索引](https://inet.omnetpp.org/docs/showcases/tsn/trafficshaping/)
3. [INET Asynchronous Shaper showcase](https://github.com/inet-framework/inet/tree/9097c7b3a64dd31cd807d3ce51707d4540f7a633/showcases/tsn/trafficshaping/asynchronousshaper)
4. [INET CBS and ATS showcase](https://github.com/inet-framework/inet/tree/9097c7b3a64dd31cd807d3ce51707d4540f7a633/showcases/tsn/trafficshaping/cbsandats)
5. [Ieee8021qAsynchronousShaper NED 源码](https://github.com/inet-framework/inet/blob/9097c7b3a64dd31cd807d3ce51707d4540f7a633/src/inet/linklayer/ieee8021q/Ieee8021qAsynchronousShaper.ned)
6. [ATSIeee8021qFilter NED 源码](https://github.com/inet-framework/inet/blob/9097c7b3a64dd31cd807d3ce51707d4540f7a633/src/inet/linklayer/ieee8021q/ATSIeee8021qFilter.ned)
7. [AsynchronousShaper NED 源码](https://github.com/inet-framework/inet/blob/9097c7b3a64dd31cd807d3ce51707d4540f7a633/src/inet/queueing/shaper/AsynchronousShaper.ned)
8. [EligibilityTimeMeter C++ 源码](https://github.com/inet-framework/inet/blob/9097c7b3a64dd31cd807d3ce51707d4540f7a633/src/inet/protocolelement/shaper/EligibilityTimeMeter.cc)
9. [EligibilityTimeFilter C++ 源码](https://github.com/inet-framework/inet/blob/9097c7b3a64dd31cd807d3ce51707d4540f7a633/src/inet/protocolelement/shaper/EligibilityTimeFilter.cc)
10. [TokenBucketMeter NED 源码](https://github.com/inet-framework/inet/blob/9097c7b3a64dd31cd807d3ce51707d4540f7a633/src/inet/queueing/meter/TokenBucketMeter.ned)
11. [OMNeT++ 6.4.0 release](https://github.com/omnetpp/omnetpp/releases/tag/omnetpp-6.4.0)
12. [INET 4.7.0 release](https://github.com/inet-framework/inet/releases/tag/v4.7.0)
13. [OMNeT++ Manual](https://doc.omnetpp.org/omnetpp/manual/)
