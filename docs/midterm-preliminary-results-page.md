# 中期答辩 preliminary 实验结果页设计

> 用途：将当前 preliminary 实验结果整理成 PPT 中可直接使用的 3-4 页结果展示。  
> 核心口径：当前实验用于阶段性趋势验证，不作为最终论文定量结论；重点说明“动态场景下静态配置存在问题、Rule-Based 有改善趋势、但与 Offline-Optimized 仍有差距”。

---

## 1. 实验结果页总体安排

建议将 preliminary 实验结果拆成 4 页：

| 页码 | 主题 | 主要材料 | 核心结论 |
|---|---|---|---|
| 实验结果页 1 | 实验设计与对比方法 | 动态场景、deadline profile、四组方法、指标 | 说明数据怎么来、比较什么 |
| 实验结果页 2 | 四组指标对比 | `metrics_bar_relaxed.svg` + relaxed 表格 | Static-Low 在动态场景下明显失效，Rule-Based 相比 Static-Low 有改善趋势，而当前 CIR/CBS 离散搜索空间下的 Offline-Optimized 候选显示规则库仍有差距。 |
| 实验结果页 3 | 动态过程分析 | `delay_timeseries_relaxed.svg` + `cir_cbs_trajectory_relaxed.svg` | Rule-Based 能动态调参，但 CIR 提升仍不足 |
| 实验结果页 4 | 规则触发与预标定 | `rule_timeline_relaxed.svg` + 预标定表 | 规则库已开始标定，偏向 CIR 的策略更有效 |

如果 PPT 时间有限，可以压缩为 2 页：

1. 四组指标对比；
2. 规则触发与预标定。

---

# 实验结果页 1：实验设计与对比方法

## 推荐标题

```text
Preliminary 实验设计
```

## 页面布局

建议分为四块：

### 左上：动态场景

```text
低负载初始阶段
  ↓
高峰流量增加
  ↓
ET burst 突发注入
  ↓
负载回落
```

### 右上：Deadline profiles

| Profile | 含义 | 用途 |
|---|---|---|
| relaxed | 10ms PoC deadline | 展示规则调整趋势 |
| strict | 350us / 600us 文献 deadline | 对齐文献严格要求 |

### 左下：对比方法

| 方法 | 含义 |
|---|---|
| Static-Low | 低谷静态配置 |
| Static-High | 手工高配置 |
| Offline-Optimized | 当前 CIR/CBS 离散网格搜索空间下的静态较优候选 |
| Rule-Based | 在线规则库方法 |

### 右下：评价指标

```text
drop rate
deadline violation rate
TT/ET P95 / P99 delay
rule trigger counts
CIR/CBS trajectory
```

## 可用数据/文件

- `ats-sim/config/traffic_literature.yaml`
- `ats-sim/config/scenario_literature.yaml`
- `ats-sim/results/rule_compare_with_offline_relaxed.json`
- `ats-sim/results/rule_compare_with_offline_strict.json`

## 页面底部标注

建议加一行小字：

```text
Note: 当前结果为 preliminary single-hop Python/SimPy PoC，用于趋势验证，不作为最终论文定量结论。
```

## 讲稿简短版

本阶段实验采用文献参数映射和人工动态场景设计。动态场景包括低负载、高峰、突发和回落四个阶段。为了区分 PoC 趋势展示和文献严格要求，设置了 relaxed 和 strict 两种 deadline profile。对比方法包括 Static-Low、Static-High、Offline-Optimized 和 Rule-Based，指标主要包括丢包率、时延违约率、P95/P99 时延以及规则触发情况。

---

# 实验结果页 2：四组方法指标对比

## 推荐标题

```text
四组方法 preliminary 对比结果
```

## 推荐图表

优先放：

```text
ats-sim/results/figures/metrics_bar_relaxed.svg
```

如果空间允许，可在右侧或下方放 relaxed 表格。

## relaxed profile 表格

| 方法 | 初始/最终 CIR-CBS | 丢包率 | TT/ET P99 | 违约率 |
|---|---:|---:|---:|---:|
| Static-Low | 8Mbps / 20Kbit | 39.53% | 254.217 ms | 98.78% |
| Static-High | 30Mbps / 100Kbit | 0.30% | 71.008 ms | 60.30% |
| Offline-Optimized | 50Mbps / 10Kbit | 0.00% | 0.387 ms | 0.00% |
| Rule-Based | 8/20 → 26.4/131.8 | 0.00% | 56.841 ms | 42.11% |

## strict profile 可作为补充

如果要提 strict，只建议放一句：

```text
strict profile 下，当前 grid candidate 的 violation rate 为 0.04%（8/22035），这仅表示其满足 PoC 的 `epsilon=1%` 可行门限；Rule-Based 为 52.61%，说明当前规则库仍需进一步标定和高保真验证。
```

不要在主图中过多展开 strict，否则会让页面显得负面且难解释。

## 页面核心结论

建议用三条：

1. Static-Low 在动态场景下明显失效；
2. Rule-Based 相比 Static-Low 明显降低丢包和违约；
3. Offline-Optimized 显示当前规则库仍有明显优化空间。

## 讲稿简短版

从 relaxed profile 的结果可以看到，Static-Low 在动态场景下丢包率达到 39.53%，违约率接近 98.78%，说明低谷静态配置无法适应高峰和突发流量。Rule-Based 将丢包率降为 0，违约率也明显下降，说明在线调整 CIR/CBS 具有初步可行性。但 Offline-Optimized 的结果更好，这说明当前规则库还不是最终优化算法，后续需要进一步标定。

## 应避免的说法

不要说：

```text
Rule-Based 已经达到最优。
```

建议说：

```text
Rule-Based 相比低静态配置具有明显改善趋势，但与 Offline-Optimized 仍有差距。
```

---

# 实验结果页 3：动态过程分析

## 推荐标题

```text
动态过程分析：时延曲线与 CIR/CBS 轨迹
```

## 推荐图表

建议左右排版：

### 左侧图

```text
ats-sim/results/figures/delay_timeseries_relaxed.svg
```

### 右侧图

```text
ats-sim/results/figures/cir_cbs_trajectory_relaxed.svg
```

## 图表解读

### 时延曲线

重点看：

- Static-Low 在高峰阶段时延明显升高；
- Offline-Optimized 基本保持较低时延；
- Rule-Based 能缓解时延，但仍明显高于 Offline-Optimized。

### CIR/CBS 轨迹

重点看：

- Rule-Based 从 8Mbps / 20Kbit 出发；
- 最终约为 26.4Mbps / 131.8Kbit；
- Offline-Optimized 静态参考为 50Mbps / 10Kbit；
- 当前规则库对 CIR 提升不足，CBS 增长偏多。

## 页面核心结论

```text
当前规则库已经能动态调整参数，但其调整方向和强度仍需标定；当前场景更需要提升 CIR，而不是过多增加 CBS。
```

## 讲稿简短版

时延曲线显示，Static-Low 在负载增加后出现明显排队时延，而 Rule-Based 能通过在线调整缓解一部分问题。参数轨迹进一步说明，当前 Rule-Based 最终 CIR 只提升到约 26.4Mbps，而 Offline-Optimized 的参考值是 50Mbps；同时 Rule-Based 的 CBS 增长较多。这说明当前场景主要瓶颈更偏向 CIR，后续规则库应更关注服务速率提升。

---

# 实验结果页 4：规则触发与小型预标定

## 推荐标题

```text
规则触发分析与参数预标定
```

## 推荐布局

左侧放规则触发图：

```text
ats-sim/results/figures/rule_timeline_relaxed.svg
```

右侧放小型预标定表格。

## 预标定表格 relaxed profile

| 变体 | 最终 CIR/CBS | P99 | 违约率 |
|---|---:|---:|---:|
| Current-Rule | 26.4Mbps / 131.8Kbit | 56.841 ms | 42.11% |
| Aggressive-CIR | 12.6Mbps / 30.1Kbit | 19.819 ms | 7.52% |
| CIR-Focused-Low-CBS | 19.1Mbps / 31.6Kbit | 12.346 ms | 3.01% |
| Conservative-Return | 19.4Mbps / 51.9Kbit | 11.653 ms | 3.27% |

## 可补充 strict profile 一句话

```text
strict profile 下 Conservative-Return 将违约率从 Current-Rule 的 52.61% 降至 24.31%，但仍未达到最终要求。
```

## 页面核心结论

建议放：

```text
小型预标定表明：更偏向 CIR、减少 CBS 增长、减慢回退可显著改善 Rule-Based 表现。
```

## 讲稿简短版

为了进一步分析规则库不足，本阶段做了小型参数预标定。结果显示，相比 Current-Rule，CIR-Focused-Low-CBS 和 Conservative-Return 都显著降低了 P99 和违约率。这说明规则库不是只完成链路打通，而是已经进入参数标定阶段。不过这些结果仍然是 preliminary，后续需要在 OMNeT++ 中重新验证。

## 应避免的说法

不要说：

```text
规则库已经优化完成。
```

建议说：

```text
规则库已经开始预标定，并显示出明确优化方向；后续仍需系统标定和标准仿真验证。
```

---

## 2 页压缩版

如果 PPT 时间紧，可以压缩为两页。

### 压缩页 1：四组指标对比

标题：

```text
Preliminary 四组方法对比
```

内容：

- 放 `metrics_bar_relaxed.svg`；
- 放一张简表；
- 讲三点：
  1. Static-Low 失效；
  2. Rule-Based 有改善；
  3. Offline-Optimized 显示差距。

### 压缩页 2：规则触发与预标定

标题：

```text
规则库初步标定结果
```

内容：

- 放 `rule_timeline_relaxed.svg`；
- 放预标定表；
- 讲三点：
  1. R1-R6 可在线触发；
  2. Current-Rule 仍不足；
  3. 偏向 CIR 的变体显著改善。

---

## preliminary 标注建议

每一页实验结果底部都建议加小字：

```text
Note: Results are preliminary single-hop Python/SimPy PoC outputs, used for trend analysis only.
```

中文版本：

```text
注：当前结果为单跳 Python/SimPy proof-of-concept 初步结果，仅用于趋势分析，不作为最终论文定量结论。
```

---

## 老师质疑数据时的简短回应

如果老师问：

> 这些结果能说明什么？

建议回答：

> 当前结果主要说明三点：第一，动态负载下低静态配置确实容易失效；第二，在线调整 CIR/CBS 相比低静态配置有明显改善趋势；第三，与 Offline-Optimized 的差距说明规则库还需要进一步标定。因此这些数据用于中期阶段的趋势验证，而最终结论会依赖后续 OMNeT++/INET 高保真仿真。

如果老师问：

> 这些数据能作为论文最终实验吗？

建议回答：

> 不能直接作为最终定量结论。当前是 preliminary PoC，后续会在 OMNeT++/INET 中复现 baseline 和规则库，并做多 seed、多场景和参数敏感性分析。

---

## 推荐在 PPT 中优先使用的结果

### 主展示使用 relaxed profile

原因：

- relaxed 更适合展示规则趋势；
- 图表更直观；
- 不会因为 strict 过严导致中期展示偏负面。

### strict profile 放补充说明

建议用一句话：

```text
strict profile 用于对齐文献 deadline，目前仍存在违约，说明后续需要标准仿真和进一步标定。
```

---

## 本部分的总结句

可在实验结果最后一页使用：

> Preliminary 结果表明，动态负载下低静态 ATS 参数配置会明显失效；基于状态反馈的 Rule-Based 方法能够降低丢包和违约率，但与 Offline-Optimized 仍有差距。小型预标定进一步表明，规则库优化方向应更偏向 CIR 提升和回退控制。后续将在 OMNeT++/INET 中进行高保真验证。
