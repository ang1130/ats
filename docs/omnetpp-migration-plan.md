# OMNeT++/INET 迁移计划

> 本文档用于中期后工作衔接：将当前 Python/SimPy ATS proof-of-concept 转向 OMNeT++/INET 或相关 TSN 仿真平台进行更高保真度验证。
>
> 当前 Python/SimPy 结果均为 preliminary / proof-of-concept，不替代最终标准仿真。

---

## 1. 迁移动机

当前 `ats-sim/` 已经完成：

- 基于文献参数的流量配置；
- 单跳 ATS/CIR-CBS 简化仿真；
- R1-R6 规则库初版；
- Static-Low / Static-High / Offline-Optimized / Rule-Based 四组 preliminary 对比；
- relaxed / strict deadline profile；
- preliminary 图表生成。

但当前仿真仍是自实现 Python/SimPy 单跳 PoC，存在以下限制：

1. 不是完整 IEEE 802.1Qcr ATS 实现；
2. MRT 仅在理论和配置中保留，未完整实现 residence time / drop 行为；
3. 未建模多跳交换、复杂队列和完整 TSN 协议栈；
4. 流量为文献映射 + 人工动态场景，不是真实工业 trace；
5. 规则阈值尚未经过标准仿真和多场景验证。

因此，中期后应将当前 PoC 中沉淀的规则逻辑、参数范围和 baseline 迁移到 OMNeT++/INET 或类似 TSN 仿真平台，进行更高保真度验证。

---

## 2. 当前 PoC 与 OMNeT++/INET 的分工

| 项目 | 当前 Python/SimPy PoC | 后续 OMNeT++/INET |
|---|---|---|
| 主要目的 | 快速验证问题必要性、规则逻辑和参数范围 | 标准化、高保真仿真验证 |
| 网络规模 | 单跳简化链路 | 单交换机起步，后续多跳/多交换机 |
| ATS 模型 | 简化 CIR/CBS 令牌桶近似 | 使用 INET TSN/ATS 模块或自定义 ATS 模块 |
| MRT | 理论/配置占位，当前 Python 执行模型未实现 residence-time 或 MRT drop | 在 INET 中逐步实现/对齐 residence time 和丢弃逻辑 |
| 流量 | 文献参数映射 + 人工动态事件 | 复现文献流量，扩展多场景 |
| 规则库 | Python `RuleEngine` 原型 | controller / simple module / listener 形式迁移 |
| 数据用途 | preliminary 趋势验证 | 论文正式实验依据 |

结论：Python PoC 的目标不是替代 OMNeT++，而是作为规则库设计和参数预筛选平台。

---

## 3. 可迁移内容

### 3.1 可迁移的研究逻辑

当前 PoC 中最有价值、可迁移的不是底层 SimPy 代码，而是以下设计：

1. 研究问题：动态负载下静态 ATS 参数配置失效；
2. 决策变量：`x = (CIR, CBS, MRT)`，当前阶段重点为 `(CIR, CBS)`；
3. 状态变量：`q, λ, d_obs, σ, token_level, drop_flag`；
4. 规则库 R1-R6；
5. 对比方法：Static-Low / Static-High / Offline-Optimized / Rule-Based；
6. 指标：drop rate、deadline violation rate、TT/ET P95/P99、资源占用；
7. deadline profile：strict literature deadline 与 relaxed prototype deadline；
8. Offline-Optimized 网格搜索结果，用作静态 baseline 候选。

### 3.2 当前 PoC 到 OMNeT++ 的映射

| 当前 PoC 文件/概念 | OMNeT++/INET 中的迁移方式 |
|---|---|
| `traffic_literature.yaml` | 转换为 `.ini` / XML / NED 中的 application traffic 参数 |
| `scenario_literature.yaml` | 转换为动态流量启动/停止、burst 注入事件 |
| `ATSShaper` | 替换为 INET ATS/TSN queueing 模块；若不足则自定义 simple module |
| `EgressLink` | 使用 INET link、queue、scheduler 模块 |
| `Monitor` | 使用 OMNeT++ signals/statistics/listeners 采集状态 |
| `RuleEngine` | 迁移为 controller 模块或 C++/Python co-simulation 控制逻辑 |
| `run_offline_grid_search.py` | 可作为 OMNeT++ 参数扫描脚本的设计参考 |
| `plot_preliminary_results.py` | 可复用为 OMNeT++ 输出结果的后处理图表脚本思路 |

---

## 4. 目标 OMNeT++ 最小拓扑

中期后不建议一开始搭复杂工业网络，应先从最小可验证拓扑开始。

建议拓扑：

```text
Talker_1  ─┐
Talker_2  ─┼── TSN Switch ── Listener
Talker_3  ─┘
BE Source ─┘
```

流量类型：

| 流量 | 说明 |
|---|---|
| High-priority control | 周期 500us，150B，deadline 350us |
| Medium-priority flow | 周期 1000us，750B，deadline 600us |
| BE background | 500B，间隔 280-520us 或等效随机背景流 |
| ET burst | 动态事件中注入，用于模拟告警/急停 |

动态场景：

```text
低负载初始阶段
  ↓
增加 high/medium flows，模拟负载上升
  ↓
注入 ET burst，模拟突发告警
  ↓
移除部分 flows，模拟负载回落
```

---

## 5. OMNeT++ 中的四组 baseline

应优先复现当前 Python PoC 中已经形成的四组对比：

| 方法 | OMNeT++ 中的配置方式 |
|---|---|
| Static-Low | 固定 CIR=8Mbps, CBS=20Kbit |
| Static-High | 固定 CIR=30Mbps, CBS=100Kbit |
| Offline-Optimized | 使用当前网格搜索候选 CIR=50Mbps, CBS=10Kbit 起步，后续可在 OMNeT++ 中重新搜索 |
| Rule-Based | 初始 CIR=8Mbps, CBS=20Kbit，运行时根据 controller 调整 |

注意：

- 当前 `50Mbps / 10Kbit` 是 Python PoC 下的 preliminary 搜索结果；
- 迁移到 OMNeT++ 后必须重新验证，不应直接视为最终最优；
- 但它可以作为初始搜索范围和 baseline 候选。

---

## 6. Rule-Based controller 迁移设计

### 6.1 输入状态

在 OMNeT++ 中需要采集或计算：

| 状态 | 可能来源 |
|---|---|
| 队列长度 `q` | queue length signal |
| 到达速率 `λ` | packet received / packet pushed 统计 |
| 观测时延 `d_obs` | end-to-end delay 或 residence time 统计 |
| 突发强度 `σ` | 滑动窗口到达速率方差 |
| token / shaper state | 若 INET 模块暴露；否则可先不使用或用 queue/delay 替代 |
| drop flag | packet drop signal |

### 6.2 输出动作

控制器需要能够：

```text
set CIR
set CBS
optionally set MRT in later stage
```

如果 INET 模块支持运行时参数修改，则直接更新模块参数。
如果不支持，需要考虑：

1. 自定义 ATS simple module；
2. 使用 controller + 参数化 queue/meter；
3. 先用多静态配置分段模拟动态调整；
4. 或将在线控制逻辑放入自定义 C++ 模块。

### 6.3 初始规则

迁移初版仍使用当前 R1-R6：

| 规则 | 含义 |
|---|---|
| R1_QUEUE_GROW | 队列增长且到达率上升，增加 CIR |
| R2_DELAY_WARN | 时延接近 deadline，增加 CIR/CBS |
| R3_BURST | 突发强度升高，增加 CBS |
| R4_RESOURCE_EXCESS | 连续低负载，降低 CIR |
| R5_DROP | 出现丢包，紧急扩容 |
| R6_RETURN | 稳态时回归默认配置 |

OMNeT++ 阶段需要重点验证：

- 当前规则是否仍然改善 Static-Low；
- 与 Offline-Optimized 静态配置差距是否存在；
- CIR/CBS 动作是否需要重新标定；
- MRT 是否需要纳入控制。

---

## 7. 迁移步骤

### 阶段 1：平台调研

目标：确认 OMNeT++/INET 对 ATS/Qcr 的支持情况。

任务：

- 确认 INET 版本；
- 查找是否已有 ATS / Asynchronous Shaper / Eligibility Time Meter / Per-stream filtering/policing 模块；
- 确认是否支持 CIR/CBS/MRT 或等价参数；
- 确认是否支持运行时参数调整；
- 若不支持，确定自定义模块方案。

### 阶段 2：最小拓扑复现

目标：不接入规则库，先复现静态 baseline。

任务：

- 搭建单交换机拓扑；
- 配置 high-priority / medium / BE / burst 流量；
- 复现 Static-Low、Static-High、Offline-Optimized；
- 输出 delay、drop、queue length、throughput。

### 阶段 3：动态场景复现

目标：复现低负载-高峰-burst-回落场景。

任务：

- 实现流量启动/停止；
- 实现 burst 注入；
- 对比静态配置在动态场景下的表现；
- 与 Python PoC 趋势对照。

### 阶段 4：规则库迁移

目标：接入 Rule-Based controller。

任务：

- 周期采样状态；
- 实现 R1-R6；
- 动态调整 CIR/CBS；
- 记录规则触发日志；
- 与 Static-Low / Static-High / Offline-Optimized 对比。

### 阶段 5：扩展验证

目标：形成论文级实验。

任务：

- 多 seed；
- 多负载强度；
- 多 burst 模式；
- 多拓扑；
- 参数敏感性；
- 与文献 baseline 对比；
- 如可行，纳入 MRT。

---

## 8. 风险点与应对

| 风险 | 影响 | 应对 |
|---|---|---|
| INET 不支持完整 802.1Qcr ATS | 无法直接标准复现 | 使用近似模块或自定义 ATS simple module |
| 运行时不能修改 CIR/CBS | Rule-Based 在线控制受限 | 自定义 controller/shaper 或分阶段参数模拟 |
| OMNeT++ 配置复杂、调试慢 | 进度风险 | 先复现最小单交换机拓扑，再扩展 |
| Python PoC 参数不能直接迁移 | 结果不一致 | 将 Python 结果定位为预筛选，OMNeT++ 中重新标定 |
| strict deadline 过严 | 违约率高 | 同时保留 strict 与 relaxed 两种 profile，明确解释用途 |
| MRT 建模困难 | 理论变量与执行模型尚未对齐 | INET Stage 1 明确 MRT 固定配置并核验行为，Stage 2 再扩展在线控制 |

---

## 9. 中期答辩表述建议

可在中期材料中这样表述：

> 本阶段首先搭建 Python/SimPy 单跳 PoC 平台，用于快速验证动态 ATS 参数调整问题的必要性、规则库设计逻辑和参数范围。该平台不替代最终标准仿真，而是作为快速原型和参数预筛选工具。中期后将基于当前已形成的流量配置、baseline、状态变量和 R1-R6 规则库，迁移至 OMNeT++/INET 平台开展高保真验证。

---

## 10. 中期后计划时间表

| 阶段 | 目标 | 预计产出 |
|---|---|---|
| 第 1 阶段 | OMNeT++/INET ATS 支持调研 | 模块调研记录、可行方案 |
| 第 2 阶段 | 最小 TSN 拓扑搭建 | Static baseline 初步结果 |
| 第 3 阶段 | 动态场景复现 | 动态负载下静态配置表现 |
| 第 4 阶段 | Rule-Based controller 接入 | 规则库 OMNeT++ 对比结果 |
| 第 5 阶段 | 多场景/多 seed/参数敏感性 | 论文正式实验数据 |

---

## 11. 当前 PoC 对后续工作的实际贡献

当前 Python/SimPy PoC 对后续 OMNeT++ 工作的贡献不是代码直接复用，而是：

1. 明确动态负载下静态配置失效的问题；
2. 明确 ATS 参数建模应使用 CIR/CBS/MRT；
3. 形成 R1-R6 规则库初版；
4. 发现 R4 过早降速等规则问题；
5. 通过 Offline-Optimized 搜索发现当前瓶颈更偏向 CIR；
6. 提供 Static-Low / Static-High / Offline-Optimized / Rule-Based 四组 baseline 设计；
7. 提供图表和指标体系；
8. 为后续 OMNeT++ 复现提供参数范围和实验模板。

因此，当前 PoC 应作为“快速原型验证与参数预标定”写入中期材料，而不是作为最终仿真平台。
