# 中期报告文字版大纲

> 用途：用于撰写研究生中期报告 Word / PDF 正文。  
> 题目：动态工业物联网中异步流量整形优化研究  
> 当前阶段定位：基于文献参数完成 Python/SimPy 单跳 preliminary PoC，形成规则库初版、四组对比、小型规则预标定，并规划中期后 OMNeT++/INET 高保真仿真。  
> 注意：当前所有实验数据均应标注 preliminary / proof-of-concept，不作为最终论文定量结论。

---

## 建议报告结构

```text
1. 研究背景与意义
2. 国内外研究现状与文献阅读进展
3. 开题后研究方案修正
4. ATS 参数建模与规则库设计
5. Preliminary PoC 仿真实验平台
6. Preliminary 实验结果与分析
7. 当前问题与局限性
8. 中期后工作计划
9. 总结
```

---

# 1. 研究背景与意义

## 本节目的

说明为什么研究动态工业物联网中的 ATS 参数自适应优化是有意义的。

## 建议写作内容

### 1.1 工业物联网实时通信需求

可写：

> 工业物联网场景中存在大量周期控制流、事件触发流和背景数据流。控制流和告警流通常具有较高实时性要求，需要网络提供低时延、低丢包和较强的确定性保障。随着工业设备数量增加和业务模式动态变化，网络流量会呈现出低负载、高峰负载、突发告警和负载回落等动态特征，传统静态配置方法难以持续适应这种变化。

### 1.2 TSN 与 ATS 的研究意义

可写：

> 时间敏感网络 TSN 为工业以太网提供了确定性通信机制。其中，TAS 适合强周期和强同步流量，但依赖全局时间同步和静态调度表；ATS 作为异步流量整形机制，能够更灵活地适应非周期和突发流量，因此适合作为动态工业物联网中的关键流量整形机制。然而，ATS 的 CIR、CBS、MRT 等参数通常提前配置，面对动态流量变化时可能出现高峰期配置不足或低谷期资源浪费的问题。

### 1.3 本课题研究问题

可写：

> 因此，本课题围绕动态工业物联网中 ATS 参数配置问题，研究如何根据网络状态自适应调整 ATS 参数，以降低关键流量的时延违约率和丢包率，同时控制资源占用。

## 可配图/表

- TAS 与 ATS 对比表；
- 动态流量变化示意图；
- 研究问题框图。

---

# 2. 国内外研究现状与文献阅读进展

## 本节目的

说明开题后进行了文献阅读，并根据文献修正了研究方案。

## 建议写作内容

### 2.1 TAS/Qbv 相关研究

可写：

> TAS/Qbv 相关研究主要关注基于时间门控的确定性调度。相关文献为 TSN 中时间触发流量的调度建模和确定性通信提供了理论基础，但其依赖时间同步和静态调度表，在动态异步流量场景下灵活性不足。

### 2.2 ATS/Qcr 相关研究

可写：

> ATS/Qcr 通过异步方式对流量进行整形，避免了 TAS 对全局时间门控的强依赖，更适合异步、突发和非周期流量。文献中通常使用 CIR、CBS、MRT 等参数描述 ATS 整形行为，这也促使本课题将早期的 `(r,b)` 表述修正为 `(CIR,CBS,MRT)`。

### 2.3 ATS 参数优化与在线调整相关研究

可写：

> 部分研究关注 ATS 参数优化，例如通过离线优化方法选择静态参数配置；也有研究关注 TSN 中在线准入控制、带宽分配和动态调度问题。这些工作说明了静态参数优化和在线调整在工业 TSN 场景中的重要性，也为本课题设计 Offline-Optimized baseline 和 Rule-Based 在线调整方法提供了依据。

### 2.4 当前文献阅读对本课题的影响

可写：

> 经过第一轮文献阅读，本课题在三个方面进行了修正：第一，将 ATS 参数建模从 `(r,b)` 修正为 `(CIR,CBS,MRT)`；第二，将短期 PoC 的执行重点聚焦在 CIR/CBS 在线调整，MRT 仅保留为理论/配置占位量而未在执行模型中实施 residence-time 约束；第三，引入 Offline-Optimized 静态基线，避免只将规则法与低静态配置进行对比。

## 可配表

| 文献方向 | 对本课题的作用 |
|---|---|
| IEEE 802.1Qcr / ATS | 提供 ATS 参数与机制依据 |
| Yoshimura & Ito | 提供 ATS 静态优化 baseline 参考 |
| Yu 等在线带宽分配 | 支撑在线调整思路 |
| Craciunas Qbv/TAS | 提供 TSN 确定性调度背景 |
| OMNeT++/INET/CyclicSim | 后续高保真仿真平台参考 |

---

# 3. 开题后研究方案修正

## 本节目的

说明当前方案不是随意偏离开题，而是根据文献和实验进行了合理修正。

## 建议写作内容

### 3.1 参数模型修正

可写：

> 开题阶段初步使用令牌桶参数 `(r,b)` 描述 ATS 整形行为。经过文献阅读后，发现 ATS 相关研究通常采用 CIR、CBS 和 MRT 作为参数描述。因此，当前理论模型修正为：

```text
x = (CIR, CBS, MRT)
```

> 其中 CIR 表示承诺信息速率，CBS 表示承诺突发大小，MRT 表示最大驻留时间。

### 3.2 阶段性实现范围

可写：

> 考虑到 MRT 涉及标准 ATS 中 residence time 和丢弃行为，当前 Python/SimPy PoC 只执行 CIR/CBS 的在线调整：

```text
x_stage1 = (CIR, CBS)
```

> MRT 仍保留在理论模型和配置中，但当前执行模型未实施 residence-time/MRT drop 约束；后续将在 OMNeT++/INET 等更标准仿真平台中进一步实现和验证。

### 3.3 仿真路线修正

可写：

> 开题阶段计划采用仿真平台验证 ATS 参数优化方法。考虑到规则库设计需要频繁修改状态变量、阈值和动作策略，本阶段首先搭建 Python/SimPy 单跳 PoC，用于快速验证问题必要性和规则逻辑。该 PoC 不替代最终标准仿真，中期后将迁移到 OMNeT++/INET 进行高保真验证。

## 可配表

使用 `docs/midterm-progress-comparison.md` 中的开题计划 vs 当前进展对照表。

---

# 4. ATS 参数建模与规则库设计

## 本节目的

系统描述状态变量、决策变量、目标函数和规则库。

## 建议写作内容

### 4.1 决策变量

可写：

> 本课题将 ATS 参数优化变量定义为：

```text
x(t) = (CIR(t), CBS(t), MRT(t))
```

> 当前阶段执行中，在线调整变量为：

```text
x_stage1(t) = (CIR(t), CBS(t))
```

> MRT 仅保留为理论/配置占位量，当前执行模型不施加 residence-time/MRT drop 约束。

### 4.2 状态变量

可写：

> 规则库根据监测状态进行决策，当前状态向量定义为：

```text
s(t) = {q(t), λ(t), d_obs(t), σ(t), token(t), drop(t)}
```

其中：

| 状态变量 | 含义 |
|---|---|
| `q` | ATS 队列长度 |
| `λ` | 到达速率 |
| `d_obs` | 观测时延 |
| `σ` | 突发强度 |
| `token` | token 水位 |
| `drop` | 丢包标志 |

### 4.3 优化目标

可写：

> 目标是在动态流量下同时降低关键流量时延违约率、丢包率和高分位时延，并尽量控制资源占用。可表示为多目标优化问题：

```text
minimize: deadline_violation_rate, drop_rate, P95/P99 delay, resource_cost
```

其中资源代价可近似为：

```text
resource_score = CIR / link_bandwidth + α · CBS / CBS_max
```

### 4.4 R1-R6 规则库

可写：

> 当前规则库采用轻量级、可解释的状态反馈方式，包括 R1-R6 六类规则。

| 规则 | 触发条件 | 动作 | 目的 |
|---|---|---|---|
| R1_QUEUE_GROW | 队列增长且到达率上升 | 增加 CIR | 应对持续负载上升 |
| R2_DELAY_WARN | 观测时延接近 deadline | 增加 CIR/CBS | 提前避免违约 |
| R3_BURST | 突发强度升高 | 增加 CBS | 吸收突发 |
| R4_RESOURCE_EXCESS | 连续低负载 | 降低 CIR | 释放资源 |
| R5_DROP | 出现丢包 | 紧急扩容 | 降低丢包 |
| R6_RETURN | 稳态运行 | 回归默认 | 避免长期过配 |

### 4.5 R4 迟滞修正

可写：

> 初版 R4 在队列短暂为空和 token 水位较高时就降低 CIR，导致高峰阶段可能过早回退。为此，加入扩容后保持时间、连续低负载窗口和更小降速步长，使 R4 触发次数从 23 次下降到 5 次，降低了规则振荡风险。

---

# 5. Preliminary PoC 仿真实验平台

## 本节目的

说明当前仿真平台架构和定位。

## 建议写作内容

### 5.1 平台定位

可写：

> 当前仿真平台为 Python/SimPy 单跳 PoC，主要用于快速验证动态负载下静态 ATS 参数失效问题、规则库触发逻辑和参数调整趋势。该平台不替代后续 OMNeT++/INET 标准仿真。

### 5.2 仿真架构

可写：

```text
TT/ET 流 → ATS Shaper → EgressLink → 接收统计
BE 流   → EgressLink → 接收统计
```

> ATS 只服务 TT/ET 关键流量，BE 流量绕过 ATS 直接进入出口链路，并通过严格优先级调度与关键流竞争链路资源。

### 5.3 实验配置

可写：

> 当前实验采用 `traffic_literature.yaml` 和 `scenario_literature.yaml`。流量周期、包大小和 deadline 主要参考文献参数映射，动态场景包括低负载、高峰流量增加、ET burst 注入和负载回落。

### 5.4 数据可信度声明

必须写：

> 当前所有仿真结果均为 preliminary / proof-of-concept，主要用于趋势分析和中期阶段性展示，不作为最终论文定量结论。后续需要通过 OMNeT++/INET、多 seed、多场景和参数敏感性分析进一步验证。

---

# 6. Preliminary 实验结果与分析

## 本节目的

展示四组对比、规则预标定和结果分析。

## 建议写作内容

### 6.1 四组对比方法

可写：

| 方法 | 含义 |
|---|---|
| Static-Low | 低谷静态配置 |
| Static-High | 手工高配置 |
| Offline-Optimized | CIR/CBS 网格搜索静态基线 |
| Rule-Based | 在线规则库方法 |

### 6.2 relaxed profile 结果

可写：

| 方法 | 丢包率 | TT/ET P99 | 违约率 |
|---|---:|---:|---:|
| Static-Low | 39.53% | 254.217 ms | 98.78% |
| Static-High | 0.30% | 71.008 ms | 60.30% |
| Offline-Optimized | 0.00% | 0.387 ms | 0.00% |
| Rule-Based | 0.00% | 56.841 ms | 42.11% |

分析：

> Static-Low 在动态场景下出现严重丢包和违约，说明低谷静态配置无法适应高峰和突发流量。Rule-Based 相比 Static-Low 明显改善，说明在线调整 CIR/CBS 具有初步可行性。但 Rule-Based 与 Offline-Optimized 仍有明显差距，说明当前规则库仍需进一步标定。

### 6.3 strict profile 结果

可写：

| 方法 | 丢包率 | TT/ET P99 | 违约率 |
|---|---:|---:|---:|
| Static-Low | 39.53% | 254.217 ms | 99.78% |
| Static-High | 0.30% | 71.008 ms | 69.05% |
| Offline-Optimized | 0.00% | 0.387 ms | 0.04% |
| Rule-Based | 0.00% | 56.841 ms | 52.61% |

分析：

> strict profile 使用文献中更严格的 350us / 600us deadline。当前 Rule-Based 在 strict profile 下仍有较高违约率，说明当前规则库和简化 PoC 尚不足以满足严格实时要求，需要后续标准仿真和进一步规则标定。

### 6.4 小型规则参数预标定

可写：

| 变体 | P99 | 违约率 |
|---|---:|---:|
| Current-Rule | 56.841 ms | 42.11% |
| Aggressive-CIR | 19.819 ms | 7.52% |
| CIR-Focused-Low-CBS | 12.346 ms | 3.01% |
| Conservative-Return | 11.653 ms | 3.27% |

分析：

> 小型预标定表明，更偏向 CIR、减少 CBS 增长、减慢回退可以明显改善 Rule-Based 表现。这说明规则库已经开始进入参数标定阶段，但仍未达到最终优化要求。

### 6.5 可引用图表

- `ats-sim/results/figures/metrics_bar_relaxed.svg`
- `ats-sim/results/figures/delay_timeseries_relaxed.svg`
- `ats-sim/results/figures/cir_cbs_trajectory_relaxed.svg`
- `ats-sim/results/figures/rule_timeline_relaxed.svg`

---

# 7. 当前问题与局限性

## 本节目的

主动说明当前工作边界，避免过度承诺。

## 建议写作内容

可写：

> 当前工作仍存在以下局限：

1. 当前仿真为 Python/SimPy 单跳 PoC，不是完整 IEEE 802.1Qcr ATS；
2. MRT 仅为理论/配置占位量，尚未在 Python 执行模型中实现 maximum residence time 约束或相关丢弃行为；
3. 流量参数来自文献映射，动态场景为人工设计，不是真实工业 trace；
4. 规则库仅完成初版和小型预标定，尚未系统优化；
5. 当前实验主要为单场景、固定随机种子，缺少多 seed、多场景；
6. 尚未完成 OMNeT++/INET 高保真验证。

总结句：

> 因此，当前结果主要用于说明研究问题的必要性和方法方向的初步可行性，最终结论仍需后续标准仿真和系统实验支持。

---

# 8. 中期后工作计划

## 本节目的

说明后续工作不是泛泛而谈，而是有明确路线。

## 建议写作内容

### 8.1 OMNeT++/INET 迁移

可写：

> 中期后将优先推进 OMNeT++/INET 高保真验证。迁移计划包括：

1. 调研 INET 对 ATS/Qcr、eligibility time、CIR/CBS/MRT 的支持情况；
2. 搭建最小单交换机 TSN 拓扑；
3. 复现 Static-Low、Static-High、Offline-Optimized baseline；
4. 将 R1-R6 规则库迁移为 controller 或 simple module；
5. 扩展多 seed、多场景、多拓扑实验。

### 8.2 规则库优化

可写：

> 后续将基于当前小型预标定结果，进一步系统分析 `cir_up`、`cbs_up`、`cooldown`、`return_ratio` 等规则参数对性能的影响，并开展消融实验。

### 8.3 论文级实验完善

可写：

> 最终论文实验将重点补充标准仿真、多场景、多 seed、参数敏感性以及与静态优化 baseline 的系统对比。

## 可配表

| 阶段 | 工作 | 产出 |
|---|---|---|
| 阶段 1 | INET ATS/Qcr 支持调研 | 可行性方案 |
| 阶段 2 | 最小 TSN 拓扑搭建 | 静态 baseline 结果 |
| 阶段 3 | 动态场景复现 | 静态配置失效验证 |
| 阶段 4 | Rule-Based controller 接入 | 规则法对比结果 |
| 阶段 5 | 多场景/多 seed/参数敏感性 | 论文正式实验数据 |

---

# 9. 总结

## 本节目的

收束全文，强调阶段性成果和后续计划。

## 建议写作内容

可写：

> 本阶段围绕动态工业物联网中的 ATS 参数优化问题，完成了从开题设想到 preliminary PoC 的阶段性推进。首先，基于文献阅读将 ATS 参数模型由 `(r,b)` 修正为 `(CIR,CBS,MRT)`；其次，设计并实现了基于状态反馈的 R1-R6 规则库初版；随后，搭建 Python/SimPy 单跳 PoC 平台，完成 Static-Low、Static-High、Offline-Optimized 和 Rule-Based 四组 preliminary 对比；最后，根据 Offline-Optimized 结果进行了小型规则参数预标定，并制定了中期后 OMNeT++/INET 高保真仿真迁移计划。

> 当前结果表明，动态流量下低静态 ATS 配置会明显失效，在线调整 CIR/CBS 具有初步可行性。但当前结果仍是 preliminary，规则库尚需系统标定，最终结论需依赖后续 OMNeT++/INET 标准仿真、多场景和多 seed 实验。

---

# 可直接放入报告的“阶段性成果”列表

1. 完成 ATS/TSN 第一轮文献阅读和参数整理；
2. 将 ATS 参数模型从 `(r,b)` 修正为 `(CIR,CBS,MRT)`；
3. 构建基于文献参数的 `traffic_literature.yaml` 与动态场景；
4. 实现 Python/SimPy 单跳 PoC；
5. 实现 R1-R6 自适应规则库初版；
6. 修正 R4 过早降速问题；
7. 实现 Offline-Optimized CIR/CBS 网格搜索；
8. 完成四组 preliminary 对比；
9. 生成中期展示图表；
10. 完成小型规则参数预标定；
11. 制定 OMNeT++/INET 迁移计划。

---

# 可直接放入报告的“后续工作”列表

1. 调研 INET/OMNeT++ 对 ATS/Qcr 的支持情况；
2. 搭建最小 TSN 仿真拓扑；
3. 在 OMNeT++ 中复现 Static-Low / Static-High / Offline-Optimized；
4. 将 R1-R6 规则库迁移为在线 controller；
5. 进一步标定 CIR/CBS 调整规则；
6. 增加多 seed、多场景和参数敏感性实验；
7. 如条件允许，扩展 MRT 建模；
8. 整理形成最终论文实验和分析。

---

# 报告写作注意事项

1. 所有当前实验数据都要标注 preliminary / proof-of-concept；
2. 不要将 Python/SimPy PoC 表述为最终标准仿真平台；
3. 不要声称 Rule-Based 已经最优；
4. 不要声称当前模型完整实现 IEEE 802.1Qcr；
5. 要主动说明 OMNeT++/INET 是中期后重点；
6. 要强调当前阶段的贡献是“问题验证 + 规则库初版 + 参数预筛选 + 迁移准备”。
