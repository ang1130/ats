# 动态 IIoT 中 ATS 参数自适应优化——形式化建模文档

> 版本：v1.1｜日期：2026-07-08  
> 用途：研究生中期答辩前的方案形式化基础。本文档基于已阅读文献，已将 ATS 决策变量从早期的 `r,b` 扩展为更规范的 `CIR/CBS/MRT`。

---

## 1. 问题概述

在动态工业物联网（IIoT）环境中，时间敏感网络（TSN）用于提供确定性低时延通信。异步流量整形器（ATS, Asynchronous Traffic Shaper, IEEE 802.1Qcr）通过基于令牌桶的逐流整形机制，为非周期、突发和异步流量提供较好的确定性保障能力。

然而，ATS 的关键参数通常采用静态或离线方式配置。当工业网络中的流量负载、任务数量、突发事件和拓扑状态发生变化时，静态参数容易出现两类问题：

1. **高峰期配置不足**：CIR/CBS/MRT 设置过低或过紧，导致排队时延增大、超过时延约束，甚至触发丢弃；
2. **低谷期配置过度**：按高峰需求配置会造成带宽和缓存资源长期浪费。

因此，本研究关注的问题是：

> 如何在动态 IIoT 场景中，以轻量、可解释、低开销的方式实现 ATS 参数的在线自适应优化？

本研究将 ATS 参数配置问题建模为一个**动态多目标优化问题（Dynamic Multi-Objective Optimization Problem, DMOP）**，并采用**基于规则库与离线标定的自适应启发式策略**进行近似在线求解。

---

## 2. ATS 机制与参数定义

### 2.1 ATS 基本机制

根据 ATS 相关文献与 IEEE 802.1Qcr 机制描述，ATS 是一种基于 per-stream / per-class 思想的异步整形机制，其核心包括：

- 对进入的帧计算 **eligibility time**，即该帧最早允许发送的时间；
- 使用令牌桶机制控制发送资格；
- 当令牌不足时，帧需要等待未来令牌积累；
- 当帧等待时间超过最大驻留时间限制时，可能被丢弃；
- ATS 不依赖全局门控时隙，因此相较 TAS 更适合异步、突发和非周期流量。

### 2.2 ATS 关键参数

基于 Yoshimura & Ito 2025 以及 Lübeck et al. 2025 对 ATS 参数的描述，ATS 的典型关键参数包括：

| 参数 | 含义 | 对应早期符号 | 单位 | 作用 |
|---|---|---|---|---|
| **CIR** | Committed Information Rate，承诺信息速率 / 令牌恢复速率 | `r` | bits/s | 决定令牌恢复速度，影响长期可服务速率 |
| **CBS** | Committed Burst Size，承诺突发大小 / 令牌桶容量 | `b` | bits | 决定可吸收的突发规模 |
| **MRT** | Max Residence Time，最大驻留时间 | — | s | 限制帧在整形器中允许等待的最长时间，超过可能丢弃 |

因此，本研究将 ATS 参数向量定义为：

$$
\mathbf{x} = (CIR, CBS, MRT)
$$

### 2.3 本阶段实现范围

考虑到一个月内需要形成可展示的中期成果，同时 MRT 的动态调整涉及更复杂的丢弃策略和有界性分析，本阶段采取分阶段策略：

- **理论建模层面**：将决策变量完整定义为 $(CIR, CBS, MRT)$；
- **当前 Python 原型实现层面**：MRT 作为配置占位量保留；执行模型不施加 residence-time/MRT drop 约束，仅对 CIR 与 CBS 进行自适应调整；
- **中期后扩展**：在 OMNeT++/INET 或 CyclicSim 迁移阶段进一步加入 MRT 的动态调整与有界性验证。

因此，当前阶段的实际控制变量为：

$$
\mathbf{x}_{stage1} = (CIR, CBS), \quad MRT = MRT_0
$$

---

## 3. 符号定义

### 3.1 决策变量

完整决策变量：

$$
\mathbf{x}(t_k) = (CIR(t_k), CBS(t_k), MRT(t_k)) \in \mathcal{X}
$$

其中：

$$
\mathcal{X}=\{(CIR,CBS,MRT) \mid CIR_{min}\le CIR\le CIR_{max},\ CBS_{min}\le CBS\le CBS_{max},\ MRT_{min}\le MRT\le MRT_{max}\}
$$

当前阶段不将 MRT 作为执行模型参数或在线优化变量：它仅保留为理论/配置占位量；当前 Python 执行模型只作用于 CIR/CBS，未施加 residence-time/MRT drop 约束。

### 3.2 状态/观测量

设决策时刻为 $t_k$，状态向量为：

$$
\mathbf{s}(t_k)=\big(q(t_k),\lambda(t_k),\tau(t_k),d_{obs}(t_k),\sigma(t_k),p_{drop}(t_k)\big)
$$

| 符号 | 含义 |
|---|---|
| $q(t_k)$ | ATS 队列长度 |
| $\lambda(t_k)$ | 短期平均到达速率，滑动窗口估计 |
| $\tau(t_k)$ | 当前令牌桶水位，通常归一化为 $\tau/CBS$ |
| $d_{obs}(t_k)$ | 近期端到端时延观测值，如滑动窗口 P95/P99 |
| $\sigma(t_k)$ | 流量负载波动度，用于识别突发或阶跃变化 |
| $p_{drop}(t_k)$ | 近期丢包/丢弃事件标志或丢包率 |

其中 \(\tau(t_k)\) 在当前 PoC 中为虚拟 release 排程的令牌盈余/缺口近似，可为负；其实现语义见 [`ats-sim/docs/state-semantics.md`](../ats-sim/docs/state-semantics.md)，不应将其视为始终处于 \([0,1]\) 的物理 token fill ratio。

### 3.3 动态性建模

工业网络中的动态性主要来自：

1. 活跃流集合 $\mathcal{F}(t)$ 变化；
2. 流量到达速率 $\lambda(t)$ 变化；
3. 突发事件导致短时流量尖峰；
4. 不同任务类型的 QoS 要求动态切换。

因此，给定状态 $\mathbf{s}(t_k)$ 下的最优参数 $\mathbf{x}^*(t_k)$ 会随时间漂移：

$$
\mathbf{x}^*(t_k) \ne \mathbf{x}^*(t_{k+1})
$$

这就是本研究中“动态多目标优化”的含义：**不是目标函数形式频繁变化，而是网络状态变化导致最优 ATS 参数随时间变化。**

---

## 4. 目标函数

给定状态 $\mathbf{s}(t_k)$ 与 ATS 参数 $\mathbf{x}(t_k)$，定义多目标函数：

$$
\mathbf{F}(\mathbf{x},\mathbf{s})=
\begin{bmatrix}
f_1=\bar{d}(\mathbf{x},\mathbf{s}) \\
f_2=J(\mathbf{x},\mathbf{s}) \\
f_3=P_{drop}(\mathbf{x},\mathbf{s}) \\
f_4=-\Theta(\mathbf{x},\mathbf{s}) \\
f_5=R_{cost}(\mathbf{x},\mathbf{s})
\end{bmatrix}
$$

| 目标 | 含义 | 优化方向 |
|---|---|---|
| $f_1$ | 平均端到端时延 | 最小化 |
| $f_2$ | 时延抖动，如 P99-P1 或方差 | 最小化 |
| $f_3$ | 丢包率（当前 PoC 为 shaper queue overflow；MRT 违约丢弃留待后续标准仿真） | 最小化 |
| $f_4$ | 吞吐量的负值 | 最小化，即最大化吞吐 |
| $f_5$ | 资源占用成本，如过高 CIR/CBS/MRT | 最小化 |

### 4.1 硬实时优先的标量化目标

本阶段场景暂定为硬实时优先，因此将时延、抖动和违约率置于更高权重。可采用加权和形式：

$$
f(\mathbf{x},\mathbf{s}) = w_1f_1+w_2f_2+w_3f_3+w_4f_4+w_5f_5
$$

其中：

$$
\sum_{i=1}^{5}w_i=1,\quad w_i\ge0
$$

硬实时场景下通常取：

$$
w_1,w_2,w_3 > w_4,w_5
$$

即优先保证确定性时延，再考虑吞吐与资源利用率。

---

## 5. 约束条件

$$
\begin{aligned}
\text{C1（时延可靠性约束）:}&\quad \Pr[D_{e2e}\le D_{max}]\ge 1-\epsilon \\
\text{C2（MRT 约束）:}&\quad D_{residence}\le MRT \\
\text{C3（速率可行域）:}&\quad CIR_{min}\le CIR\le CIR_{max} \\
\text{C4（突发容量可行域）:}&\quad CBS_{min}\le CBS\le CBS_{max} \\
\text{C5（MRT 可行域）:}&\quad MRT_{min}\le MRT\le MRT_{max} \\
\text{C6（稳定性约束）:}&\quad CIR\ge \bar{\lambda}_{critical} \\
\text{C7（防抖约束）:}&\quad \|\mathbf{x}(t_k)-\mathbf{x}(t_{k-1})\|\le \Delta_{max}
\end{aligned}
$$

其中：

- $D_{e2e}$ 为端到端时延；
- $D_{residence}$ 为帧在 ATS 整形器中的驻留时间；
- $D_{max}$ 为业务时延红线；
- $\epsilon$ 为允许违约概率；
- $\bar{\lambda}_{critical}$ 表示关键流的长期平均到达速率；
- C7 用于防止参数在短时间内频繁震荡。

### 5.1 当前阶段约束简化

当前 Python 单跳原型中：

- MRT 仅作为理论/配置占位量保留；执行模型不施加 residence-time/MRT drop 约束；
- 重点控制 $CIR$ 与 $CBS$；
- 用 `10ms` 作为初始 $D_{max}$，用于 proof-of-concept；
- 未来可根据 Yoshimura & Ito 的工业网络参数进一步使用 `350μs`、`600μs` 等更严格要求。

---

## 6. 动态多目标优化问题形式化

完整问题为：

$$
\mathbf{x}^*(t_k)=\arg\min_{\mathbf{x}\in\mathcal{X}}\mathbf{F}(\mathbf{x},\mathbf{s}(t_k))
$$

subject to C1–C7。

当前阶段简化为：

$$
(CIR^*(t_k),CBS^*(t_k))=\arg\min_{CIR,CBS} \mathbf{F}((CIR,CBS,MRT_0),\mathbf{s}(t_k))
$$

由于在线精确求解开销较大，本文采用规则库策略近似求解。

---

## 7. 自适应规则库策略

将在线策略表示为：

$$
\pi: \mathbf{s}(t_k)\rightarrow \Delta\mathbf{x}(t_k)
$$

规则库形式：

$$
\pi=\{\rho_i: Cond_i(\mathbf{s};\theta_i)\rightarrow \Delta\mathbf{x}_i\}_{i=1}^{N}
$$

当前阶段：

$$
\Delta\mathbf{x}_i=(\Delta CIR_i,\Delta CBS_i,0)
$$

其中 $MRT_0$ 只表示理论分阶段建模中的固定占位量；当前 Python 执行模型不实现其 residence-time/MRT drop 语义。

典型规则包括：

| 状态 | 动作 | 直觉 |
|---|---|---|
| 队列增长且到达速率上升 | 增大 CIR | 提高长期服务能力 |
| P95/P99 时延逼近红线 | 增大 CIR，必要时增大 CBS | 优先保障确定性时延 |
| 检测到短时突发 | 增大 CBS | 提高突发吸收能力 |
| 队列长期为空且令牌长期接近满桶 | 降低 CIR | 减少资源占用 |
| 丢弃/违约发生 | 增大 CIR/CBS；未来可调整 MRT | 紧急恢复确定性保障 |
| 长时间稳定 | 向默认/离线优化配置回归 | 防止过度配置 |

### 7.1 事件触发 + 节流

采用事件触发，而非固定周期强制调整：

- 当状态指标越过阈值时触发规则；
- 两次参数调整之间设置最小间隔 $T_{cool}$；
- $T_{cool}$ 通过消融实验确定，如 100ms、300ms、500ms、1s、2s。

---

## 8. 离线阈值标定

规则库中的阈值 $\theta$ 和调整步长 $\Delta$ 不应完全手工指定，而应通过离线仿真标定。

### 8.1 标定流程

1. 构造多组静态与动态流量场景；
2. 对每个场景使用网格搜索或 Downhill Simplex / Nelder-Mead 搜索近似最优 $(CIR,CBS,MRT)$；
3. 对当前阶段，只搜索 $(CIR,CBS)$；MRT 不进入 Python PoC 的执行或搜索；
4. 根据状态—最优参数样本拟合规则阈值；
5. 在未参与标定的动态场景中验证规则库性能。

### 8.2 与 Yoshimura & Ito 的关系

Yoshimura & Ito 2025 使用 Downhill Simplex 方法离线搜索 ATS 参数，使工业网络满足时延需求。本研究将该类离线优化方法作为：

1. **对比基线**：Offline-Optimized ATS；
2. **规则标定工具**：用离线搜索结果反推在线规则阈值。

本研究的区别在于：Yoshimura & Ito 是静态离线配置，本研究关注动态场景下的在线参数自适应。

---

## 9. 实验设定

### 9.1 拓扑

当前阶段采用单跳或单瓶颈简化拓扑：

```text
TT/ET 流 -> ATS -> 出口链路 -> 接收端
BE 流    -> 出口链路 -> 接收端
```

中期后扩展到 OMNeT++/INET 或 CyclicSim 的多交换机拓扑。

### 9.2 流量类型

| 类型 | 特征 | 文献依据 |
|---|---|---|
| 控制流 / TT | 周期性、小包、严格时延 | Craciunas Qbv；Yoshimura & Ito |
| 中优先级流 | 周期性或准周期，大包，中等时延 | Yoshimura & Ito |
| ET 突发流 | 告警、事件触发、短时突发 | Yu et al.；HTS 场景 |
| BE 背景流 | 无硬时延要求，制造竞争负载 | TSN 仿真常见背景流 |

### 9.3 文献参数基准

Yoshimura & Ito 2025 给出的工业网络参数可作为后续仿真配置来源：

| 类型 | 周期/间隔 | 包长 | 优先级 | 时延要求 |
|---|---:|---:|---:|---:|
| 高优先级控制流 | 500 μs | 150 B | 7 | 350 μs |
| 中优先级流 | 1000 μs | 750 B | 6 | 600 μs |
| 背景/无要求流 | 280–520 μs | 500 B | 5 | NA |

当前 Python 原型可先使用放宽后的时延约束进行 proof-of-concept，但正式报告需标注其简化性质。

---

## 10. 对比基线

后续实验至少应包含以下基线：

| 基线 | 含义 | 用途 |
|---|---|---|
| Static-Low | 按低谷负载配置 CIR/CBS | 资源省，但高峰易违约 |
| Static-High | 按高峰负载配置 CIR/CBS | 时延好，但低谷浪费资源 |
| Offline-Optimized | 参考 Yoshimura & Ito 的离线搜索配置 | 直接静态优化基线 |
| Fixed-Rule | 规则库但阈值未标定 | 验证标定价值 |
| Rule-Based Adaptive | 本文方法 | 目标方案 |

核心叙事应为：

> Static-Low 动态下违约；Static-High 长期过度配置；Offline-Optimized 静态有效但不能在线响应；Rule-Based Adaptive 在动态阶段提高 CIR/CBS，在稳定阶段回退，兼顾时延保障与资源利用。

---

## 11. 评价指标

| 指标 | 含义 |
|---|---|
| 平均端到端时延 | 基本性能 |
| P95/P99 时延 | 硬实时尾部时延 |
| 时延抖动 | 确定性稳定程度 |
| $D_{max}$ 违约率 | 关键约束是否满足 |
| 丢包率 / MRT 违约丢弃率 | 可靠性 |
| 吞吐量 | 网络有效传输能力 |
| 平均 CIR / 峰值 CIR | 带宽资源占用 |
| 平均 CBS / 峰值 CBS | 缓冲资源占用 |
| 规则触发次数 | 控制开销与稳定性 |
| 决策耗时 | 轻量性指标 |

---

## 12. 与已有工作的区分

| 工作 | 类型 | 主要内容 | 与本研究区别 |
|---|---|---|---|
| Craciunas et al. 2016 | 静态确定性调度 | Qbv/TAS 离线调度，保证确定性时延 | TAS 静态调度，不关注 ATS 在线参数自适应 |
| Yoshimura & Ito 2025 | ATS 离线参数优化 | Downhill Simplex 搜索 MRT/CIR/CBS | 离线静态配置，对初始值敏感；本研究在线自适应 |
| Lübeck et al. 2025 | ATS 有界性分析 | 非 FIFO/FRER 场景下避免无界延迟 | 关注机制有界性与配置放置；本研究关注动态 IIoT 参数反馈调整 |
| 李琳等 2025 HTS | 混合整形 | 5G-TSN 融合下异构流量整形器 | 多机制组合，配置复杂；本研究聚焦 ATS 参数自适应 |
| Yu et al. 2025 | 在线准入控制 | TSN/ATS+CBS 中 ET 流在线 admission control 与带宽分配 | 关注准入与带宽分配；本研究关注 ATS CIR/CBS/MRT 参数 |
| Wu et al. 2023 | 轻量反馈调度 | token bucket + WFQ，基于队列长度调整权重 | 非 TSN/ATS；本研究将轻量反馈思想迁移到 ATS 参数 |

---

## 13. 当前阶段边界声明

当前阶段为中期前 proof-of-concept：

- 使用 Python/SimPy 单跳简化仿真；
- ATS 模型实现 CIR/CBS 令牌桶核心；
- MRT 在理论和配置中保留，但当前 Python 执行模型不实现 residence-time/MRT drop 约束；
- 流量为基于文献参数构造的合成流量；
- 所有实验结果需标注 preliminary；
- 中期后迁移 OMNeT++/INET 或 CyclicSim，并补充 MRT、自适应标定和多跳验证。

---

## 14. 未来工作

1. 将 MRT 纳入在线调整；
2. 使用 OMNeT++/INET 或 CyclicSim 验证；
3. 引入多跳拓扑和真实工业 profile；
4. 增加预测式自适应，例如轻量时间序列预测；
5. 与 Downhill Simplex、网络微积分方法结合，提升规则标定质量。
