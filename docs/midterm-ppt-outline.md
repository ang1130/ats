# 中期答辩 PPT 详细页纲

> 题目：动态工业物联网中异步流量整形优化研究  
> 当前定位：Python/SimPy PoC 阶段已基本收口，用于快速原型验证、规则库预标定和中期阶段性展示；中期后迁移到 OMNeT++/INET 做高保真标准仿真。  
> 注意：当前所有实验结果均为 preliminary / proof-of-concept，不作为最终论文定量结论。

---

## 推荐 PPT 总体结构

建议控制在 **15-16 页**。如果答辩时间较短，可压缩到 12 页左右。

核心叙事线：

```text
研究背景与问题
  ↓
开题目标回顾
  ↓
文献修正与 ATS 参数建模
  ↓
规则库初版设计
  ↓
Python/SimPy PoC 定位
  ↓
Preliminary 实验设计与结果
  ↓
规则库小型预标定
  ↓
当前局限性
  ↓
OMNeT++/INET 迁移计划
```

---

# 第 1 页：标题页

## 标题

```text
动态工业物联网中异步流量整形优化研究
——中期进展汇报
```

## 页面内容

- 姓名；
- 学号；
- 专业；
- 导师；
- 日期。

## 讲稿要点

本课题围绕 TSN 中 ATS 异步流量整形机制，研究动态工业物联网场景下 ATS 参数 CIR/CBS/MRT 的自适应优化问题。本次汇报主要介绍开题以来完成的文献修正、规则库设计、PoC 仿真验证、初步结果和后续 OMNeT++ 仿真计划。

---

# 第 2 页：研究背景与问题

## 标题

```text
研究背景：动态工业物联网对确定性通信的需求
```

## 页面内容

建议放 3 个层次：

```text
工业物联网
  ↓
多类型业务流：控制流 / 告警流 / 背景流
  ↓
动态变化：设备上线、任务切换、突发告警
  ↓
时延、丢包、确定性要求
```

可以做成一张简单流程图。

## 关键点

- 工业物联网中存在周期控制流、事件触发流、背景流；
- 流量不是静态的，存在高峰、突发和回落；
- 网络需要低时延、低丢包和可预测性；
- TSN 是工业确定性通信的重要方案。

## 讲稿要点

工业物联网中的业务流具有明显的动态性。一方面，控制流需要较低时延；另一方面，设备状态变化、任务切换和告警事件会带来突发负载。因此，静态配置的流量整形参数可能难以适应动态场景。

---

# 第 3 页：ATS 与研究问题

## 标题

```text
ATS 参数静态配置在动态场景下的挑战
```

## 页面内容

建议用表格对比 TAS 和 ATS：

| 机制 | 特点 | 局限 |
|---|---|---|
| TAS / Qbv | 基于时间门控，确定性强 | 依赖时间同步，调度表静态 |
| ATS / Qcr | 异步整形，更适合非周期/突发流 | 参数配置复杂，通常静态 |

引出 ATS 关键参数：

```text
CIR / CBS / MRT
```

研究问题：

```text
动态流量变化下，如何自适应调整 ATS 参数，降低时延违约和丢包，同时控制资源占用？
```

## 讲稿要点

ATS 相比 TAS 更适合异步和突发流量，但其 CIR、CBS、MRT 等参数通常提前配置。当负载从低谷进入高峰时，低配置会导致违约；而长期高配置又会造成资源浪费。因此本课题研究动态场景下 ATS 参数的自适应优化。

---

# 第 4 页：开题目标回顾与当前进展

## 标题

```text
开题目标与当前阶段进展
```

## 页面内容

建议用对照表：

| 开题阶段计划 | 当前进展 |
|---|---|
| 阅读 TSN/ATS 相关文献 | 已完成第一轮文献整理，接入文献参数 |
| 建立 ATS 参数模型 | 已从 `(r,b)` 修正为 `(CIR,CBS,MRT)` |
| 设计自适应规则库 | 已实现 R1-R6 规则库初版 |
| 搭建仿真验证环境 | 已完成 Python/SimPy 单跳 PoC |
| 对比静态配置与自适应方法 | 已完成 Static-Low / Static-High / Offline-Optimized / Rule-Based 四组 preliminary 对比 |
| 后续标准仿真 | 已制定 OMNeT++/INET 迁移计划 |

## 讲稿要点

与开题阶段相比，目前主要完成了三个方面的推进：第一，基于文献将模型变量修正为 CIR/CBS/MRT；第二，实现了规则库和单跳 PoC；第三，完成了 preliminary 对比实验，并明确了中期后向 OMNeT++/INET 迁移的路线。

---

# 第 5 页：文献阅读与建模修正

## 标题

```text
文献阅读后对模型的修正
```

## 页面内容

展示从早期模型到当前模型的变化：

```text
开题初始描述：
x = (r, b)

文献修正后：
x = (CIR, CBS, MRT)

当前 PoC 阶段：
x_stage1 = (CIR, CBS)

MRT 仅作为理论/配置占位量保留；当前 Python 执行模型不实施 residence-time/MRT drop 约束。
```

参数说明表：

| 参数 | 含义 | 当前处理 |
|---|---|---|
| CIR | Committed Information Rate | 在线调整 |
| CBS | Committed Burst Size | 在线调整 |
| MRT | Max Residence Time | 理论/配置占位；当前 PoC 未执行 residence-time/MRT drop 语义 |

## 讲稿要点

早期使用 r/b 描述 ATS 参数，更多是令牌桶直觉。经过文献阅读后，发现 ATS 相关研究通常采用 CIR、CBS、MRT 表述。因此当前理论模型修正为三元参数向量；考虑到 MRT 涉及 residence time 和标准丢弃行为，本阶段 PoC 先聚焦 CIR/CBS 调整。

---

# 第 6 页：总体方法框架

## 标题

```text
基于状态反馈的 ATS 参数自适应框架
```

## 页面内容

建议画一个框图：

```text
动态流量输入
    ↓
ATS Shaper
    ↓
状态监控 Monitor
    ↓
状态 s(t)：q, λ, d_obs, σ, token, drop
    ↓
规则库 Rule Engine
    ↓
调整 CIR / CBS
    ↓
输出时延、丢包、违约率
```

## 讲稿要点

本阶段设计的是一个基于状态反馈的轻量级自适应框架。系统周期性监控队列长度、到达速率、观测时延、突发强度、token 水位和丢包标志，并根据规则库动态调整 CIR 和 CBS。

---

# 第 7 页：规则库设计

## 标题

```text
R1-R6 规则库初版设计
```

## 页面内容

规则表：

| 规则 | 触发条件 | 动作 | 目的 |
|---|---|---|---|
| R1_QUEUE_GROW | 队列增长且到达率上升 | 增加 CIR | 应对持续负载上升 |
| R2_DELAY_WARN | 时延接近 deadline | 增加 CIR/CBS | 提前避免违约 |
| R3_BURST | 突发强度升高 | 增加 CBS | 吸收突发流量 |
| R4_RESOURCE_EXCESS | 连续低负载 | 降低 CIR | 释放过剩资源 |
| R5_DROP | 出现丢包 | 紧急扩容 | 降低丢包 |
| R6_RETURN | 稳态运行 | 回归默认值 | 避免长期过配 |

页面底部补充：

```text
机制：cooldown + 防抖 + R4 迟滞
```

## 讲稿要点

规则库的设计目标是轻量、可解释、便于后续迁移。每条规则对应一种网络状态和参数动作。为避免频繁振荡，加入了 cooldown、防抖以及 R4 迟滞机制。

---

# 第 8 页：规则库迭代问题：R4 过早降速

## 标题

```text
规则库迭代：R4 过早降速问题与修正
```

## 页面内容

建议做成“问题—原因—修正—效果”四段：

| 项 | 内容 |
|---|---|
| 问题 | 初版 R4 在队列短暂为空、token 较高时立即降 CIR |
| 后果 | 高峰期可能过早回退，导致规则振荡 |
| 修正 | 增加扩容保持时间、连续低负载窗口、降低降速步长 |
| 效果 | R4 触发次数从 23 次降到 5 次 |

补充：

```text
这表明规则库已进行初步迭代，而非仅实现静态规则。
```

## 讲稿要点

初版规则运行后发现 R4_RESOURCE_EXCESS 触发过于频繁。分析后发现，系统短暂空队列并不代表高峰真正结束，因此加入迟滞机制，要求连续低负载且距离最近扩容超过保持时间才允许降速。修正后 R4 触发明显减少。

---

# 第 9 页：仿真平台定位

## 标题

```text
当前仿真平台定位：Python/SimPy PoC
```

## 页面内容

对比表：

| 项 | 当前 Python/SimPy PoC | 后续 OMNeT++/INET |
|---|---|---|
| 目的 | 快速验证规则逻辑和参数范围 | 高保真标准仿真 |
| 网络模型 | 单跳简化 | 多跳/多交换机可扩展 |
| ATS 实现 | CIR/CBS 简化近似 | TSN/ATS 模块或自定义模块 |
| MRT | 理论/配置占位，当前 PoC 未执行 residence-time/MRT drop 语义 | 后续实现并对齐 |
| 数据用途 | preliminary 趋势验证 | 论文正式实验 |

底部醒目标注：

```text
当前结果均为 preliminary / proof-of-concept，不作为最终论文定量结论。
```

Python PoC 用于前期规则逻辑探索和实验方案预筛选；最终模型与结果将在 OMNeT++/INET 中重新实现、重新验证。

## 讲稿要点

当前没有把 Python PoC 定位为最终仿真平台，而是用于快速验证问题必要性、规则触发逻辑和参数范围。中期后将迁移到 OMNeT++/INET 进行更高保真度验证。

---

# 第 10 页：实验设计

## 标题

```text
Preliminary 实验设计
```

## 页面内容

### 1. 动态场景

```text
低负载 → 高峰流量增加 → ET burst → 负载回落
```

### 2. Deadline profile

| Profile | 含义 |
|---|---|
| relaxed | 10ms PoC deadline，用于展示趋势 |
| strict | 350us / 600us 文献 deadline，用于对齐文献要求 |

### 3. 对比方法

| 方法 | 含义 |
|---|---|
| Static-Low | 低谷静态配置 |
| Static-High | 手工高配置 |
| Offline-Optimized | CIR/CBS 网格搜索静态基线 |
| Rule-Based | 在线规则库方法 |

### 4. 指标

```text
drop rate
deadline violation rate
TT/ET P95/P99 delay
CIR/CBS trajectory
rule trigger counts
```

## 讲稿要点

实验采用文献参数映射和人工动态场景。为了避免直接把严格文献 deadline 套到简化 PoC 上造成误解，设置了 relaxed 和 strict 两套 profile。对比方法包括低配置、高配置、离线优化静态配置和规则法。

---

# 第 11 页：四组对比结果

## 标题

```text
四组方法 preliminary 对比结果
```

## 页面内容

建议优先放图：

```text
ats-sim/results/figures/metrics_bar_relaxed.svg
```

同时附一张小表：

| 方法 | 丢包率 | TT/ET P99 | 违约率 |
|---|---:|---:|---:|
| Static-Low | 39.53% | 254.217 ms | 98.78% |
| Static-High | 0.30% | 71.008 ms | 60.30% |
| Offline-Optimized | 0.00% | 0.387 ms | 0.00% |
| Rule-Based | 0.00% | 56.841 ms | 42.11% |

## 讲稿要点

Static-Low 在动态场景下明显失效。Rule-Based 相比 Static-Low 将丢包率降为 0，并显著降低违约率，说明在线调整方向具有初步可行性。但与 Offline-Optimized 仍有明显差距，说明规则库还需要继续标定。

---

# 第 12 页：时延曲线与参数轨迹

## 标题

```text
动态过程分析：时延曲线与 CIR/CBS 轨迹
```

## 页面内容

建议左右两图：

左图：

```text
ats-sim/results/figures/delay_timeseries_relaxed.svg
```

右图：

```text
ats-sim/results/figures/cir_cbs_trajectory_relaxed.svg
```

## 讲稿要点

时延曲线显示 Static-Low 在高峰阶段出现明显排队时延。Rule-Based 通过在线调整 CIR/CBS 缓解了部分问题。参数轨迹显示，当前规则库最终 CIR 约为 26.4Mbps，而 Offline-Optimized 静态参考为 50Mbps，这解释了 Rule-Based 与离线优化之间的差距。

---

# 第 13 页：规则触发与小型预标定

## 标题

```text
规则触发分析与参数预标定
```

## 页面内容

建议放两块：

### 左侧：规则触发时间轴

```text
ats-sim/results/figures/rule_timeline_relaxed.svg
```

### 右侧：预标定结果表

| 变体 | P99 | 违约率 |
|---|---:|---:|
| Current-Rule | 56.841 ms | 42.11% |
| Aggressive-CIR | 19.819 ms | 7.52% |
| CIR-Focused-Low-CBS | 12.346 ms | 3.01% |
| Conservative-Return | 11.653 ms | 3.27% |

## 讲稿要点

为了回应当前规则库与 Offline-Optimized 的差距，本阶段进一步做了小型规则参数预标定。结果表明，更偏向 CIR、减少 CBS 增长、放慢回退可以明显改善 Rule-Based 表现。这说明规则库并非只完成链路打通，而是已经进入参数标定阶段。但该结果仍是 preliminary，后续将在 OMNeT++ 中继续验证。

---

# 第 14 页：当前局限性

## 标题

```text
当前局限性
```

## 页面内容

建议列 6 点：

1. 当前仿真为 Python/SimPy 单跳 PoC；
2. 尚未完整实现 IEEE 802.1Qcr ATS；
3. MRT 仅为配置占位，未在 Python 执行模型中建模 residence time 或 MRT drop；
4. 流量为文献映射 + 人工动态场景，不是真实工业 trace；
5. 规则参数仅完成小型预标定，尚未系统优化；
6. 缺少 OMNeT++/INET 高保真验证、多 seed、多场景实验。

## 讲稿要点

当前结果只用于阶段性验证，不作为最终定量结论。主要局限在于模型保真度、规则标定和实验充分性。后续工作将围绕 OMNeT++ 迁移和多场景验证展开。

---

# 第 15 页：中期后 OMNeT++/INET 迁移计划

## 标题

```text
中期后工作计划：迁移到 OMNeT++/INET 高保真验证
```

## 页面内容

建议画路线图：

```text
阶段 1：调研 INET ATS/Qcr 支持
   ↓
阶段 2：搭建最小 TSN 拓扑
   ↓
阶段 3：复现 Static baselines
   ↓
阶段 4：接入 Rule-Based controller
   ↓
阶段 5：多场景、多 seed、参数敏感性分析
```

也可以放表：

| 阶段 | 工作 | 产出 |
|---|---|---|
| 1 | 调研 INET ATS/Qcr 支持 | 可行方案 |
| 2 | 单交换机拓扑 | 静态 baseline |
| 3 | 动态场景复现 | 静态配置失效验证 |
| 4 | 规则库迁移 | Rule-Based 对比 |
| 5 | 多场景扩展 | 论文正式实验 |

## 讲稿要点

中期后将优先调研 INET 对 ATS/Qcr 的支持情况。如果已有模块支持 CIR/CBS/MRT，将基于其进行配置；如果不完整，则考虑自定义 controller 或 simple module。迁移时会复用当前阶段形成的状态变量、baseline、规则库逻辑和参数范围。

---

# 第 16 页：总结

## 标题

```text
阶段性总结
```

## 页面内容

建议用 5 条：

1. 完成 ATS 参数建模修正：`(r,b)` → `(CIR,CBS,MRT)`；
2. 搭建 Python/SimPy 单跳 PoC，用于快速验证和参数预筛选；
3. 实现 R1-R6 规则库初版，并修正 R4 过早降速问题；
4. 完成四组 preliminary 对比和小型规则预标定；
5. 明确中期后向 OMNeT++/INET 高保真仿真迁移。

最后一句：

```text
当前结果证明方向具有初步可行性，但最终结论需依赖后续标准仿真和系统实验验证。
```

## 讲稿要点

本阶段主要完成了从开题设想到可运行 PoC 的转化。当前结果说明动态 ATS 参数自适应具有研究必要性和初步可行性，但仍需通过 OMNeT++/INET 标准仿真、多场景和参数敏感性分析进一步验证。

---

# 时间较短时的 12 页压缩版

如果答辩时间只有 8-10 分钟，可以压缩为：

1. 标题；
2. 背景与问题；
3. ATS 参数建模；
4. 当前总体进展；
5. 规则库设计；
6. PoC 平台定位；
7. 实验设计；
8. 四组对比结果；
9. 规则预标定；
10. 局限性；
11. OMNeT++ 迁移计划；
12. 总结。

---

# 中期答辩核心表述口径

## 口径 1：当前不是最终仿真

建议说：

> 当前 Python/SimPy 平台用于快速原型验证，不替代 OMNeT++/INET 标准仿真。

## 口径 2：规则库不是最终完成，但已经开始标定

建议说：

> 当前规则库为初版，已完成 R1-R6 和 R4 迟滞修正，并进行了小型参数预标定；后续将在 OMNeT++ 中进一步优化和验证。

## 口径 3：当前结果是 preliminary

建议说：

> 当前实验结果仅用于说明趋势和阶段性进展，不作为最终论文定量结论。

---

# 建议优先放入 PPT 的图

## 必放

1. `ats-sim/results/figures/metrics_bar_relaxed.svg`
2. `ats-sim/results/figures/delay_timeseries_relaxed.svg`
3. `ats-sim/results/figures/cir_cbs_trajectory_relaxed.svg`
4. `ats-sim/results/figures/rule_timeline_relaxed.svg`

## 可选

5. strict profile 表格；
6. `ats-sim/results/figures/metrics_bar_strict.svg`；
7. 规则预标定表。

---

# 当前材料是否足够

按这个 PPT 结构，目前材料已经足够支撑中期阶段性答辩。当前拥有：

- 背景；
- 文献修正；
- 建模；
- 规则库；
- PoC；
- 实验；
- 图表；
- 预标定；
- 局限性；
- OMNeT++ 迁移计划。

关键是不要过度承诺，应将当前阶段定位成：

```text
PoC 收口 + 中期后标准仿真准备
```
