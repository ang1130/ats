# 开题计划 vs 当前进展对照表

> 用途：中期答辩 PPT / 中期报告中说明“开题后完成了哪些工作、哪些发生了合理调整、哪些转入中期后工作”。  
> 核心口径：当前工作基本符合开题预期，已经完成 PoC 阶段闭环；但最终 OMNeT++/INET 高保真仿真与论文级实验仍属于后续重点。

---

## 1. 详细对照表

| 开题答辩设想 / 计划 | 当前完成情况 | 证明材料 / 文件 | 中期表述建议 |
|---|---|---|---|
| 研究动态工业物联网中 ATS 参数优化问题 | **已保持一致** | 开题材料；当前文档与代码均围绕 ATS / CIR / CBS / MRT | 研究方向未改变，仍聚焦动态工业物联网中 ATS 参数自适应优化 |
| 分析 TSN 中 TAS 与 ATS 的适用场景 | **已完成初步梳理** | `ats-sim/docs/literature-notes.md`；中期材料背景部分 | TAS 适合强确定性周期流，ATS 更适合异步、突发和非周期流量 |
| 阅读 TSN/ATS 相关文献 | **已完成第一轮阅读整理，仍需继续补充** | `ats-sim/docs/literature-notes.md`；`docs/ats-references.md` 如有 | 已阅读并整理第一轮核心文献，后续继续精读 802.1Qcr、INET/OMNeT++ 相关资料 |
| 建立 ATS 参数形式化模型 | **已完成关键修正** | `docs/ats-formalization.md` | 开题初期用 `(r,b)` 表述，文献阅读后修正为更标准的 `(CIR,CBS,MRT)` |
| 研究 CIR/CBS/MRT 对时延和资源的影响 | **已完成 CIR/CBS 初步验证，MRT 暂固定** | `ats-sim/config/traffic_literature.yaml`；`ats-sim/experiments/run_offline_grid_search.py`；`ats-sim/experiments/run_rule_calibration.py` | 当前阶段聚焦 CIR/CBS，MRT 涉及标准 residence time 行为，放入中期后扩展 |
| 构建动态流量场景 | **已完成 preliminary 动态场景** | `ats-sim/config/scenario_literature.yaml` | 已构造低负载—高峰—突发—回落动态场景，用于验证静态参数失效和规则调整趋势 |
| 接入文献参数 | **已完成初步接入** | `ats-sim/config/traffic_literature.yaml` | 当前流量周期、大小、deadline 等参数来自文献映射，但仍属于 preliminary 配置 |
| 设计轻量级自适应规则库 | **已完成初版并迭代** | `ats-sim/src/rule_engine.py` | 已实现 R1-R6 规则、cooldown、防抖、R4 迟滞，规则库可在线调整 CIR/CBS |
| 规则库根据状态动态调整 ATS 参数 | **已实现** | `ats-sim/experiments/run_rule_compare.py`；`ats-sim/experiments/run_compare_with_offline.py` | Monitor 采集队列、到达速率、时延、突发强度、token、drop 状态，RuleEngine 根据规则调整 CIR/CBS |
| 通过实验验证静态配置在动态场景下的问题 | **已完成** | `ats-sim/results/rule_compare_with_offline_relaxed.json`；`ats-sim/results/rule_compare_with_offline_strict.json` | Static-Low 在动态场景下丢包率和违约率很高，证明研究问题具有必要性 |
| 对比静态配置与规则法 | **已完成 preliminary 对比** | `ats-sim/experiments/run_compare_with_offline.py`；结果 JSON；图表 | 已完成 Static-Low / Static-High / Offline-Optimized / Rule-Based 四组对比 |
| 引入优化静态 baseline | **已完成初步 Offline-Optimized 网格搜索** | `ats-sim/experiments/run_offline_grid_search.py`；`ats-sim/results/offline_grid_literature_*.json` | 已用 CIR/CBS 网格搜索得到离线静态优化候选，避免只和低配置比较 |
| 分析规则库不足并进行改进 | **已开始** | `ats-sim/experiments/run_rule_calibration.py`；`ats-sim/results/rule_calibration_*.json` | 已根据 Offline-Optimized 结果做小型规则参数预标定，发现偏向 CIR、减少 CBS 增长可显著改善结果 |
| 生成实验图表用于中期展示 | **已完成** | `ats-sim/results/figures/*.svg` | 已生成指标柱状图、时延曲线、规则触发时间轴、CIR/CBS 轨迹图 |
| 使用 OMNeT++ 或标准仿真平台验证 | **尚未完成，已制定迁移计划** | `docs/omnetpp-migration-plan.md` | 当前 Python/SimPy 是快速 PoC，不替代最终标准仿真；中期后迁移至 OMNeT++/INET |
| 完成最终论文级实验 | **未完成，属于后续工作** | 后续计划 | 需要多 seed、多场景、参数敏感性、标准仿真对标后才能形成最终定量结论 |

---

## 2. PPT 精简版

如果 PPT 页面空间有限，可以压缩成下面这张表：

| 开题计划 | 当前阶段进展 | 状态 |
|---|---|---|
| ATS 参数优化建模 | 已从 `(r,b)` 修正为 `(CIR,CBS,MRT)` | 已完成阶段性建模 |
| 文献参数接入 | 已整理文献参数并生成 `traffic_literature.yaml` | 已完成初步接入 |
| 动态场景构建 | 已构造低负载—高峰—突发—回落场景 | 已完成 |
| 规则库设计 | 已实现 R1-R6、cooldown、防抖、R4 迟滞 | 已完成初版 |
| 静态 vs 自适应对比 | 已完成四组 preliminary 对比 | 已完成 |
| 离线优化 baseline | 已实现 CIR/CBS 网格搜索 | 已完成初步版本 |
| 规则库优化 | 已完成小型参数预标定 | 进行中 |
| 标准仿真验证 | 已制定 OMNeT++/INET 迁移计划 | 中期后工作 |

---

## 3. “符合开题预期”的表述建议

可在 PPT 页面下方加入：

> 与开题阶段相比，本阶段已完成从理论设想到可运行 PoC 的转化：基于文献修正了 ATS 参数模型，接入了文献流量配置，实现了 CIR/CBS 在线规则库，并完成了四组 preliminary 对比实验。当前结果证明研究问题具有必要性，规则库方向具有初步可行性；后续将转入 OMNeT++/INET 高保真仿真和系统参数标定。

---

## 4. 需要主动解释的三点

### 4.1 为什么当前没有直接使用 OMNeT++？

建议说：

> 由于规则库设计需要频繁调整状态变量、阈值和动作策略，本阶段先采用 Python/SimPy 搭建轻量级 PoC，用于快速验证问题和参数范围。该平台不替代 OMNeT++，中期后将迁移到 OMNeT++/INET 做高保真验证。

### 4.2 为什么 MRT 暂时固定？

建议说：

> MRT 涉及 ATS 标准中的 residence time 和丢弃行为，当前单跳 PoC 尚不足以严谨评估 MRT 动态调整。因此本阶段先聚焦 CIR/CBS，后续在标准仿真平台中扩展 MRT。

### 4.3 当前 Rule-Based 是否已经达到预期？

建议说：

> 当前 Rule-Based 是规则库初版，已证明相对低静态配置具有改善趋势，但与 Offline-Optimized 仍有差距。因此本阶段进一步做了小型规则参数预标定，后续将在 OMNeT++ 中继续系统优化和验证。

---

## 5. 当前完成度评价

| 模块 | 完成度 |
|---|---|
| 文献阅读与模型修正 | 中期阶段基本完成，后续继续补充 |
| Python/SimPy PoC | 已基本收口 |
| 规则库初版 | 已完成 |
| 规则库标定 | 已开始，小型预标定完成 |
| Preliminary 实验 | 已完成 |
| 图表 | 已完成 |
| OMNeT++ 迁移计划 | 已完成 |
| 最终高保真实验 | 未完成，作为后续重点 |

---

## 6. 最适合放 PPT 的一页版本

```text
开题目标完成情况

1. 研究对象：保持为动态工业物联网中的 ATS 参数优化
2. 参数建模：由 (r,b) 修正为 (CIR,CBS,MRT)
3. 规则库：已实现 R1-R6 初版，并完成 R4 迟滞修正
4. 仿真验证：已搭建 Python/SimPy 单跳 PoC，完成四组 preliminary 对比
5. Baseline：已加入 Offline-Optimized 网格搜索基线
6. 规则标定：已完成小型参数预标定，发现 CIR 响应是关键因素
7. 后续工作：迁移到 OMNeT++/INET 进行高保真验证
```

底部加一句：

```text
当前阶段已完成 PoC 收口，后续重点转向标准仿真与系统实验。
```

---

## 7. 总体结论

当前工作基本符合开题预期，而且相比开题阶段已经有实质推进；但最终标准仿真和论文级实验仍在后续阶段。

这张对照表可用于回答：

- 现在到底做了什么？
- 和开题计划相比完成了哪些？
- 哪些没有完成？
- 为什么还没用 OMNeT++？
- 后续怎么推进？
