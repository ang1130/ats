# 开发记录 (Development Log)

> 记录 ATS 仿真项目实现过程中的问题、决策、参数变更、数据可信度。
> 方便后续回顾和答辩时回答"为什么这么做"。
> 配套: `ats-formalization.md`, `ats-rulelib-and-schedule.md`, `ats-implementation-spec.md`, `ats-references.md`

---

## ⚠️ 数据可信度声明（重要，先读）

> **历史说明。** 下文最初记录的是规则库和离线标定完成前的 Week 1 状态；其中“尚未接入规则库”“M8 尚未做”等表述不再代表当前工程状态。当前权威范围、结果台账与可复现命令见 [preliminary-experiment-protocol.md](preliminary-experiment-protocol.md)、[state-semantics.md](state-semantics.md) 和 [README](../README.md)。

当前 `ats-sim/` 产出的所有仿真数据属于 **"初步验证 (preliminary / proof-of-concept)" 性质**，
**不是严谨的最终实验结果**，不能直接作为论文最终定量结论。原因：

1. **ATS 模型是自实现的简化令牌桶**，非 IEEE 802.1Qcr 标准完整实现：
   - 省略了完整的 ER (Emptiness Reservation) 空闲预约逻辑（单跳近似）
   - 未与 OMNeT++/CyclicSim 或标准参考实现对标验证保真度
2. **流量数据是合成的**，非真实工业 trace：
   - TT 流参数取自文献典型值 (Craciunas EMSOFT 2016)，但流数量/强度为人为设定
   - BE 流参数 (8Mbps, 1500B) 是为"造出拥塞"试出来的，无真实场景对应
3. **动态场景 (scenario.yaml) 是人为设计的**，阶跃/突发的时刻和强度为演示目的设定
4. **静态默认参数 (r=8Mbps, b=20Kbit) 是为制造违约而调的**，非离线标定结果（本段为 Week 1 历史状态；后续已完成 CIR/CBS 离散网格 baseline，但不是最终标定）
5. **尚未接入规则库** (M7)，"规则法 vs 静态"对比还没做（本段为 Week 1 历史状态；后续已实现 R1–R6、R4 迟滞、四组比较和小型预标定）

**当前数据能支撑的结论（仅定性）：**
- 仿真器逻辑自洽（稳态无拥塞→0违约；动态拥塞→违约，符合令牌桶理论预期）
- "静态保守配置在动态负载下失效"这一痛点的定性验证

**当前数据不能支撑的结论：**
- 任何具体数值（如"违约率 91%"）作为最终结论 —— 这些数随参数人为变化，无普适性
- 规则法的有效性（还没实现；本段为 Week 1 历史状态，当前结论应以实验协议和四组 preliminary 结果为准）
- 与已有工作的定量对比

**正式论文实验数据需待：** OMNeT++/INET 高保真平台上的多 seed、多场景和参数敏感性验证完成后产生；当前 Python PoC 的角色是规则逻辑、实验协议和参数范围预筛选。

---

## 仿真器架构（最终版，经数次重构）

```
TT/ET 流 ──> ATS 整形器 (令牌桶 r,b) ──> EgressLink (SP优先级) ──> 接收端 (统计)
BE 流   ──────────────────────────────> EgressLink (低优先级) ──> 接收端 (统计)
```

- **ATS 只服务 TT/ET**：整形参数 (r,b) 只影响 TT/ET 的释放时机
- **BE 不经 ATS**：直接送 EgressLink，按低优先级竞争链路
- **EgressLink 严格优先级 (SP)**：TT/ET 高优先级，BE 低优先级；非抢占
- 这符合真实 TSN 中 ATS (per-class) + 优先级调度的语义

---

## 实现过程中的关键问题与决策

### 问题 1：YAML 科学计数法被解析为字符串
- **现象**：配置里 `rate: 20.0e6` 被 PyYAML (YAML 1.1) 当成字符串，导致 `rate > 0` 比较报错
- **原因**：YAML 1.1 对科学计数法格式挑剔，`20.0e6` 不被识别为浮点
- **解决**：在 `load_cfg` 加 `_to_float` + `_walk` 递归转换，把形如 `\d+(\.\d+)?[eE][+-]?\d+` 的字符串转回 float
- **位置**：`experiments/run_week1.py`, `run_week1_dynamic.py` 的 `load_cfg`
- **教训**：配置文件用 YAML 科学计数法时务必验证类型，或改用纯数字

### 问题 2：性能瓶颈（关键）
- **现象**：初版整形器 120s 仿真跑不完（数小时级），15s 也卡死
- **原因**：初版用"循环 yield + timeout 等令牌"模式，每个包多个 SimPy 事件，BE 高频到达时事件爆炸（40Mbps×1500B ≈ 3300包/s × 120s ≈ 40万包，逐包 timeout）
- **解决**：重写为"到达即算释放时刻"的链式调度：
  - 包到达时直接计算最早可释放时刻 `release_time`（基于令牌水位和队尾释放时刻）
  - 用 `_tail_release_time` 维护队尾包释放时刻，新包接其后
  - O(1) 每包，不空转
- **效果**：0.06s/10s 仿真，快约 1000 倍
- **位置**：`src/ats_shaper.py`
- **权衡**：在线改参时，已在队列中的包不回溯重排（用旧 r 算的释放时刻不变），单跳近似可接受

### 问题 3：队列长度统计虚高（popleft 时机）
- **现象**：令牌充足时队列仍持续堆积到满（1000），导致 BE 大量误丢包
- **原因**：`_deliver` 在"传输完成"（send_time + tx + prop）才 popleft，比入队晚 ~17us，这期间包都计在 queue 里
- **解决**：把 popleft 提前到"释放时刻"（send_time 那刻），即包离开整形器就出队，链路传输另算
- **位置**：`src/ats_shaper.py` `_release`
- **验证**：修复后混合 TT+BE 场景 0 丢包，发送数与理论一致

### 问题 4：BE 与 TT/ET 共用队列不合理（模型设计）
- **现象**：初版所有流量进同一个 ATS 队列，BE 流量大时淹没 TT/ET（99% 丢包），不符合 TSN 语义
- **根本原因**：真实 TSN 中 ATS 是 per-class 的，TT/ET 与 BE 不该共用一个整形器
- **解决**：重构为 ATS（只服务 TT/ET）+ EgressLink（SP 优先级，BE 直连）架构
- **位置**：新增 `src/egress.py`，重写 `src/ats_shaper.py` 去掉链路传输职责
- **意义**：模型合理性提升，BE 突发只挤压 BE 自身，不影响 TT/ET 确定性

### 问题 5：EgressLink `_wake` 名字冲突
- **现象**：`TypeError: 'NoneType' object is not callable`
- **原因**：类里用类型注解 `_wake_evt: Optional = None` 未创建实例属性，`_wake` 方法访问 `self._wake_evt` 报 AttributeError
- **解决**：在 `__init__` 显式初始化 `self._wake_event = None`，与 ATSShaper 一致的模式
- **位置**：`src/egress.py`

### 问题 6：如何制造"静态配置违约"（参数调试）
- **目标**：让静态保守配置在动态场景下出现违约，体现自适应价值
- **尝试过程**：
  1. r=50Mbps, BE=20Mbps → 0 违约（压力太小）
  2. r=10Mbps, BE=40Mbps → 99% 丢包（BE 淹没，且共用队列 bug）
  3. 修 bug + 重构后，r=20Mbps, BE=8Mbps → 0 违约（TT/ET 才 ~10Mbps < 20）
  4. r=5Mbps → 89% 违约（太极端）
  5. **r=8Mbps → 91.9% 违约、2.83% 丢包**（当前配置）
- **当前结论**：静态 r=8Mbps 在高峰 TT/ET ~12Mbps 下违约 —— 定性痛点已验证
- **注意**：违约率 91% 偏高，是因高峰期(30-90s)到达率持续 > 服务率，整个高峰期都违约。规则库(Week2)调 r 到 ~15Mbps 应能大幅降低。具体值待 Week2 验证。

---

## 参数变更记录

### `config/traffic.yaml`
| 参数 | 初值 | 当前值 | 变更原因 |
|---|---|---|---|
| `ats.r_default` | 50 Mbps | **8 Mbps** | 为制造动态违约（保守配置按低谷设） |
| `ats.b_default` | 100 Kbit | **20 Kbit** | 同上，缩小突发容量 |
| `be.rate` | 20 Mbps | **8 Mbps** | 避免 BE 淹没 TT/ET（重构后 BE 不经 ATS，但仍参与链路竞争） |
| 链路带宽 | 1 Gbps | 1 Gbps | 文献典型值，未变 |
| D_max | 10 ms | 10 ms | IEC 60802 典型值，未变 |

### `config/scenario.yaml`
| 项 | 值 | 说明 |
|---|---|---|
| duration | 120 s | 仿真总时长 |
| 初始 TT 流 | 5 条 | 稳态 ~2Mbps |
| 阶跃1 (t=30s) | +15 条 TT | 高频 1ms/2ms 流，高峰 TT/ET ~12Mbps > r=8 → 违约 |
| 突发 (t=60s) | 50 个 ET 包 | 急停告警模拟 |
| 阶跃2 (t=90s) | 移除 15 条 | 回稳态 |

---

## Week 1 里程碑达成情况

| 里程碑 | 状态 | 说明 |
|---|---|---|
| M1: 静态配置出基线曲线 | ✅ | `run_week1.py` 稳态 0 违约，0.029ms P95 |
| 动态场景验证痛点 | ✅ | `run_week1_dynamic.py` 静态 r=8 动态下 91.9% 违约 |
| 仿真器逻辑自洽 | ✅ | 稳态/动态行为符合令牌桶理论预期 |

**注意**：以上为初步验证，数据可信度见本文档顶部声明。

---

## 2026-07-08：文献阅读后的建模与配置修正

### 变更背景

读取并梳理了文件夹中的 7 篇 PDF 文献后，发现早期文档中用 `r,b` 描述 ATS 参数虽然符合令牌桶直觉，但不够贴近 ATS 文献和标准表述。Yoshimura & Ito 2025、Lübeck et al. 2025 均使用 **CIR / CBS / MRT** 描述 ATS 参数。

### 已完成变更

| 文件 | 变更 |
|---|---|
| `docs/ats-formalization.md` | 由 v1.0 更新为 v1.1，将决策变量从 `(r,b)` 扩展为 `(CIR,CBS,MRT)` |
| `docs/ats-rulelib-and-schedule.md` | 由 v1.0 更新为 v1.1，将规则动作改为 `CIR/CBS` 调整，并记录 MRT 在当时的分阶段范围说明 |
| `ats-sim/config/traffic_literature.yaml` | 新增文献参数配置，基于 Yoshimura & Ito、HTS、Craciunas 等 |
| `ats-sim/docs/literature-notes.md` | 新增 7 篇 PDF 的第一轮阅读笔记与方案修正建议 |

### 关键决策

1. **理论建模使用完整参数向量：**

   ```text
   x = (CIR, CBS, MRT)
   ```

2. **当前 Python 原型只调整 CIR/CBS：**

   ```text
   x_stage1 = (CIR, CBS), MRT = MRT0
   ```

3. **MRT 暂不在线调整**，原因：MRT 涉及 residence time 和丢弃策略，当前简化令牌桶原型不足以严谨评估。

4. **Yoshimura & Ito 2025 被确定为直接静态优化基线**，后续需实现 Offline-Optimized baseline（先用网格搜索近似 Downhill Simplex）。

5. **后续正式 preliminary 实验应逐步切换到 `traffic_literature.yaml` 的文献参数**，当前 `traffic.yaml` 仍视为调试配置。

### 数据状态声明

本轮只更新文档和配置，**没有运行新的正式仿真实验**。已有 results 中的旧数据仍然是 Week 1 调试 / proof-of-concept 数据，不得作为最终实验结论。

---

## 2026-07-08：M7 规则库与文献参数 PoC 对比

### 本轮新增/修改

| 文件 | 变更 |
|---|---|
| `src/rule_engine.py` | 新增 M7 自适应规则库引擎，实现 CIR/CBS 调整、节流、防抖、规则日志 |
| `src/ats_shaper.py` | 修正 `set_params()`：在线调整 CIR/CBS 时会对 backlog 重新计算 release time，避免“提速后旧积压包仍按旧速率释放” |
| `src/metrics.py` | 新增指标汇总工具 |
| `config/scenario_literature.yaml` | 新增基于文献参数的短时动态场景脚本 |
| `experiments/run_rule_compare.py` | 新增 Static-Low / Static-High / Rule-Based 初步对比脚本 |
| `results/rule_compare_literature.json` | 新增本轮 PoC 对比结果 |

### 实验配置

- 配置来源：`traffic_literature.yaml` + `scenario_literature.yaml`
- 仿真类型：Python/SimPy 单跳简化仿真
- ATS 在线参数：CIR/CBS
- MRT：理论/配置占位，Python 执行模型未实现 residence-time 或标准 MRT 丢弃逻辑
- 规则阈值：工程初值，**尚未经过 M8 离线标定**

### 本轮结果（Preliminary）

| 方法 | 初始 CIR/CBS | 最终 CIR/CBS | 丢包率 | TT/ET P95/P99 | 时延违约率 |
|---|---:|---:|---:|---:|---:|
| Static-Low | 8 Mbps / 20 Kbit | 8 Mbps / 20 Kbit | 39.53% | 245.367 / 254.217 ms | 99.78% |
| Static-High | 30 Mbps / 100 Kbit | 30 Mbps / 100 Kbit | 0.30% | 68.772 / 71.008 ms | 69.05% |
| Rule-Based | 8 Mbps / 20 Kbit | 14 Mbps / 300 Kbit | 0.97% | 72.663 / 82.702 ms | 38.22% |

规则触发次数：38 次，包括 `R3_BURST` 2 次、`R2_DELAY_WARN` 10 次、`R4_RESOURCE_EXCESS` 23 次、`R5_DROP` 3 次。

### 如何解读

1. **该结果仍是 preliminary，不是最终结论。**
2. Rule-Based 相比 Static-Low 明显降低了丢包率和违约率，说明在线调整 CIR/CBS 的方向是有效的。
3. Rule-Based 的 TT/ET P95/P99 仍高于 Static-High，说明当前规则阈值和步长尚不理想。
4. Rule-Based 中 `R4_RESOURCE_EXCESS` 触发过多，说明“降速/回归”规则可能过于激进，需要后续调参或离线标定。
5. 文献严格 deadline（350us/600us）对当前单跳简化模型很严，后续需要分两组指标：
   - 文献严格 deadline：用于对照 Yoshimura & Ito；
   - 放宽 prototype deadline：用于展示方法趋势。

### 下一步问题

- [ ] 调整 R4，避免在高峰期过早降 CIR；
- [ ] 增加 Rule-Based 的“高峰保持时间”或迟滞机制；
- [ ] 实现 Offline-Optimized 网格搜索，用离线最优替代手工 Static-High；
- [ ] 对 `T_cool`、`cir_up`、`cbs_up` 做消融；
- [ ] 生成时延曲线和 CIR/CBS 轨迹图。

---

## 2026-07-08：R4 迟滞修正 + deadline profile 对比

### 本轮新增/修改

| 文件 | 变更 |
|---|---|
| `src/rule_engine.py` | 为 R4 降速规则增加迟滞：高峰扩容后保持时间、连续低负载窗口、更小降速步长 |
| `experiments/run_rule_compare.py` | 增加 `--deadline-profile strict/relaxed` 参数，支持文献严格 deadline 与放宽 PoC deadline 两套口径 |
| `results/rule_compare_literature_relaxed.json` | 新增 relaxed profile 初步对比结果 |
| `results/rule_compare_literature_strict.json` | 新增 strict profile 初步对比结果 |

### R4 修正内容

旧 R4 逻辑：只要 `q≈0` 且 token 接近满桶，就立即降低 CIR。

新 R4 逻辑：必须同时满足：

1. 距离最近一次扩容超过 `hold_after_expand`；
2. 连续 `low_load_windows_for_down` 个窗口处于低负载；
3. 队列为空/接近空；
4. token 水位高；
5. 当前 CIR 高于默认 CIR。

同时将 `cir_down` 从 2Mbps 降为 1Mbps，避免过快回退。

### relaxed profile 结果（10ms PoC deadline）

| 方法 | 初始 CIR/CBS | 最终 CIR/CBS | 丢包率 | TT/ET P95/P99 | 违约率 |
|---|---:|---:|---:|---:|---:|
| Static-Low | 8 Mbps / 20 Kbit | 8 Mbps / 20 Kbit | 39.53% | 245.367 / 254.217 ms | 98.78% |
| Static-High | 30 Mbps / 100 Kbit | 30 Mbps / 100 Kbit | 0.30% | 68.772 / 71.008 ms | 60.30% |
| Rule-Based | 8 Mbps / 20 Kbit | 26.4 Mbps / 131.8 Kbit | 0.00% | 55.293 / 56.841 ms | 42.11% |

Rule-Based 触发：33 次，包括 `R3_BURST` 3 次、`R2_DELAY_WARN` 17 次、`R6_RETURN` 8 次、`R4_RESOURCE_EXCESS` 5 次。

### strict profile 结果（文献 350us/600us deadline）

| 方法 | 初始 CIR/CBS | 最终 CIR/CBS | 丢包率 | TT/ET P95/P99 | 违约率 |
|---|---:|---:|---:|---:|---:|
| Static-Low | 8 Mbps / 20 Kbit | 8 Mbps / 20 Kbit | 39.53% | 245.367 / 254.217 ms | 99.78% |
| Static-High | 30 Mbps / 100 Kbit | 30 Mbps / 100 Kbit | 0.30% | 68.772 / 71.008 ms | 69.05% |
| Rule-Based | 8 Mbps / 20 Kbit | 26.4 Mbps / 131.8 Kbit | 0.00% | 55.293 / 56.841 ms | 52.61% |

### 如何解读

1. **仍然是 preliminary，不是最终实验结论。**
2. R4 迟滞修正后，Rule-Based 的过早降速明显减少：R4 从上一轮 23 次降为 5 次。
3. Rule-Based 的丢包率从上一轮 0.97% 降到 0%，说明高峰扩容和 backlog 重调度有效。
4. Rule-Based 的违约率相比 Static-Low 明显降低，但仍偏高，说明当前规则仍未达到严格确定性要求。
5. Static-High 仍有较高违约率，说明手设 30Mbps / 100Kbit 不是真正高峰最优，应尽快实现 Offline-Optimized 网格搜索。
6. relaxed 与 strict 两套 profile 的差异说明：当前 PoC 已能展示趋势，但要对齐文献严格 deadline，需要更高 CIR/CBS 或更标准的 OMNeT++/INET ATS 实现。

### 下一步

- [ ] 实现 Offline-Optimized 网格搜索，找到真正的 Static-Optimal/Static-High；
- [ ] 生成时延曲线、CIR/CBS 轨迹图、规则触发时间轴；
- [ ] 对 `cooldown`、`cir_up`、`cbs_up` 做消融；
- [ ] 根据网格搜索结果反推规则阈值，减少手工调参。

---

## 2026-07-11：Offline-Optimized CIR/CBS 网格搜索

### 本轮新增/修改

| 文件 | 变更 |
|---|---|
| `experiments/run_offline_grid_search.py` | 新增 Offline-Optimized CIR/CBS 网格搜索脚本，复用 `run_rule_compare.py` 的配置加载和单次仿真函数 |
| `results/offline_grid_literature_relaxed.json` | 新增 relaxed profile 网格搜索结果 |
| `results/offline_grid_literature_strict.json` | 新增 strict profile 网格搜索结果 |

### 搜索配置

- 配置来源：`traffic_literature.yaml` + `scenario_literature.yaml`
- 搜索变量：CIR/CBS
- MRT：仅为 `traffic_literature.yaml` 中的配置占位，当前 Python PoC 不执行或搜索 MRT
- 搜索空间：

```text
CIR ∈ {4, 6, 8, 10, 12, 15, 20, 30, 50 Mbps}
CBS ∈ {10, 20, 50, 100, 200 Kbit}
```

### 排序目标

本轮使用“可行性优先”的选择规则：

```text
feasible = drop_rate <= 0 且 deadline_violation_rate <= epsilon
```

其中 `epsilon = 0.01`，来自 `traffic_literature.yaml` 的 `deadline.epsilon`。
若存在 feasible 候选，则优先选择资源代价最低者：

```text
resource_score = CIR / link_bandwidth + 0.1 * (CBS / max_CBS_candidate)
```

若不存在 feasible 候选，则选择 deadline violation rate、drop rate、P99 delay 综合最小的 least-bad 候选。

### relaxed profile 结果（Preliminary）

| 项 | 结果 |
|---|---:|
| Best candidate | 50 Mbps / 10 Kbit |
| feasible | True |
| resource_score | 0.5050 |
| 丢包率 | 0.00% |
| TT/ET P95/P99 | 0.277 / 0.387 ms |
| deadline violation rate | 0.00% |

### strict profile 结果（Preliminary）

| 项 | 结果 |
|---|---:|
| Best candidate | 50 Mbps / 10 Kbit |
| feasible | True (`epsilon=1%` 口径) |
| resource_score | 0.5050 |
| 丢包率 | 0.00% |
| TT/ET P95/P99 | 0.277 / 0.387 ms |
| deadline violation rate | 0.04% |

### 如何解读

1. **仍然是 preliminary，不是最终实验结论。**
2. 网格搜索表明，手设 `Static-High = 30Mbps / 100Kbit` 不是当前搜索空间下的最优静态配置。
3. 在当前单跳 PoC 和 `epsilon=1%` 口径下，`50Mbps / 10Kbit` 是 relaxed 与 strict 两套 profile 的最低资源可行候选。
4. strict profile 仍有少量 deadline violation（0.04%），因此不能表述为“严格 0 违约满足文献 deadline”，只能说在本轮 `epsilon=1%` 可行性口径下满足。
5. Offline-Optimized 的 P99 显著低于 Rule-Based，说明当前规则库还需要进一步标定，尤其需要根据离线最优结果调整扩容速度、目标 CIR 上限或状态阈值。
6. 该结果为后续四组对比提供了更严谨 baseline：`Static-Low / Static-High / Offline-Optimized / Rule-Based`。

### 下一步

- [ ] 将 Offline-Optimized 加入统一对比脚本，生成四组对比结果；
- [ ] 画图：时延曲线、CIR/CBS 轨迹、规则触发时间轴、指标柱状图；
- [ ] 基于 Offline-Optimized 结果反推规则库阈值和动作步长；
- [ ] 后续补多 seed、多场景和参数敏感性分析。

---

## 2026-07-11：四组对比与 preliminary 图表生成

### 本轮新增/修改

| 文件 | 变更 |
|---|---|
| `experiments/run_compare_with_offline.py` | 新增四组对比脚本：Static-Low / Static-High / Offline-Optimized / Rule-Based |
| `experiments/plot_preliminary_results.py` | 新增 SVG 图表生成脚本，不依赖 matplotlib |
| `results/rule_compare_with_offline_relaxed.json` | relaxed profile 四组对比结果 |
| `results/rule_compare_with_offline_strict.json` | strict profile 四组对比结果 |
| `results/figures/*.svg` | 新增指标柱状图、时延曲线、规则触发时间轴、CIR/CBS 轨迹图 |

### 四组对比结果（Preliminary）

#### relaxed profile（10ms PoC deadline）

| 方法 | 初始 CIR/CBS | 最终 CIR/CBS | 丢包率 | TT/ET P95/P99 | 违约率 |
|---|---:|---:|---:|---:|---:|
| Static-Low | 8 Mbps / 20 Kbit | 8 Mbps / 20 Kbit | 39.53% | 245.367 / 254.217 ms | 98.78% |
| Static-High | 30 Mbps / 100 Kbit | 30 Mbps / 100 Kbit | 0.30% | 68.772 / 71.008 ms | 60.30% |
| Offline-Optimized | 50 Mbps / 10 Kbit | 50 Mbps / 10 Kbit | 0.00% | 0.277 / 0.387 ms | 0.00% |
| Rule-Based | 8 Mbps / 20 Kbit | 26.4 Mbps / 131.8 Kbit | 0.00% | 55.293 / 56.841 ms | 42.11% |

#### strict profile（文献 350us/600us deadline）

| 方法 | 初始 CIR/CBS | 最终 CIR/CBS | 丢包率 | TT/ET P95/P99 | 违约率 |
|---|---:|---:|---:|---:|---:|
| Static-Low | 8 Mbps / 20 Kbit | 8 Mbps / 20 Kbit | 39.53% | 245.367 / 254.217 ms | 99.78% |
| Static-High | 30 Mbps / 100 Kbit | 30 Mbps / 100 Kbit | 0.30% | 68.772 / 71.008 ms | 69.05% |
| Offline-Optimized | 50 Mbps / 10 Kbit | 50 Mbps / 10 Kbit | 0.00% | 0.277 / 0.387 ms | 0.04% |
| Rule-Based | 8 Mbps / 20 Kbit | 26.4 Mbps / 131.8 Kbit | 0.00% | 55.293 / 56.841 ms | 52.61% |

### 生成图表

已生成：

```text
results/figures/metrics_bar_relaxed.svg
results/figures/delay_timeseries_relaxed.svg
results/figures/rule_timeline_relaxed.svg
results/figures/cir_cbs_trajectory_relaxed.svg
results/figures/metrics_bar_strict.svg
results/figures/delay_timeseries_strict.svg
results/figures/rule_timeline_strict.svg
results/figures/cir_cbs_trajectory_strict.svg
```

图表配色使用固定类别色，并通过 dataviz palette validator 检查；部分低对比颜色通过图例、直接标签和 tooltip/title 辅助识别。

### 如何解读

1. **仍然是 preliminary / PoC 图表，不是最终论文定量结果。**
2. Offline-Optimized 作为离线网格搜索静态基线，明显优于手设 Static-High，说明原 Static-High 不能作为“最优高配置”。
3. Rule-Based 相比 Static-Low 明显降低丢包和违约，但与 Offline-Optimized 仍有明显差距，说明规则阈值和动作步长需要继续标定。
4. CIR/CBS 轨迹图显示 Rule-Based 最终 CIR 只到约 26.4Mbps，而 Offline-Optimized 需要 50Mbps；这解释了 Rule-Based 的 P99 仍偏高。
5. 规则触发时间轴可用于中期报告展示规则库可解释性。

### 下一步

- [ ] 基于 Offline-Optimized 反推 Rule-Based 参数，使规则更快接近高峰所需 CIR；
- [ ] 对 `cir_up`、`cooldown`、`warn_ratio`、`hold_after_expand` 做参数消融；
- [ ] 整理中期报告/PPT，将图表和 preliminary caveat 放入实验章节；
- [ ] 后续增加多 seed、多场景验证。

---

## 2026-07-11：OMNeT++ 迁移计划与规则库小型预标定

### 本轮新增/修改

| 文件 | 变更 |
|---|---|
| `../docs/omnetpp-migration-plan.md` | 新增中期后 OMNeT++/INET 迁移计划，明确 Python PoC 与标准仿真的关系 |
| `experiments/run_rule_calibration.py` | 新增小型 Rule-Based 参数预标定实验 |
| `experiments/run_rule_compare.py` | 将默认规则参数抽出为 `default_rule_params()`，并支持 `run_once(..., rule_params=...)` 传入不同规则参数 |
| `results/rule_calibration_relaxed.json` | relaxed profile 规则参数预标定结果 |
| `results/rule_calibration_strict.json` | strict profile 规则参数预标定结果 |

### OMNeT++ 迁移计划要点

当前 Python/SimPy PoC 不作为最终标准仿真平台，而是定位为：

```text
快速原型验证 + 规则库逻辑试错 + 参数预筛选
```

中期后计划迁移到 OMNeT++/INET：

1. 调研 INET 是否支持 ATS/Qcr、eligibility time、CIR/CBS/MRT 或等价模块；
2. 搭建最小单交换机 TSN 拓扑；
3. 复现 Static-Low / Static-High / Offline-Optimized；
4. 迁移 Rule-Based controller；
5. 扩展到多 seed、多场景、多拓扑和参数敏感性分析。

### 小型规则预标定设计

动机：Offline-Optimized 显示当前场景下较优静态配置为 `50Mbps / 10Kbit`，而当前 Rule-Based 最终约为 `26.4Mbps / 131.8Kbit`，说明规则可能存在：

- CIR 提升不够快；
- CBS 增长偏多；
- 回退/保持策略仍需标定。

本轮只做小型预标定，不作为最终规则优化。比较 4 组：

| 变体 | 含义 |
|---|---|
| Current-Rule | 当前 R1-R6 工程初值 |
| Aggressive-CIR | 更快提升 CIR，适度降低 CBS 增长 |
| CIR-Focused-Low-CBS | 更偏向 CIR，显著降低 CBS 增长 |
| Conservative-Return | 减慢回退，延长扩容保持 |

### relaxed profile 预标定结果（Preliminary）

| 变体 | 最终 CIR/CBS | 丢包率 | TT/ET P95/P99 | 违约率 |
|---|---:|---:|---:|---:|
| CIR-Focused-Low-CBS | 19.1 Mbps / 31.6 Kbit | 0.00% | 8.957 / 12.346 ms | 3.01% |
| Conservative-Return | 19.4 Mbps / 51.9 Kbit | 0.00% | 8.168 / 11.653 ms | 3.27% |
| Aggressive-CIR | 12.6 Mbps / 30.1 Kbit | 0.00% | 13.827 / 19.819 ms | 7.52% |
| Current-Rule | 26.4 Mbps / 131.8 Kbit | 0.00% | 55.293 / 56.841 ms | 42.11% |

### strict profile 预标定结果（Preliminary）

| 变体 | 最终 CIR/CBS | 丢包率 | TT/ET P95/P99 | 违约率 |
|---|---:|---:|---:|---:|
| Conservative-Return | 19.4 Mbps / 51.9 Kbit | 0.00% | 8.168 / 11.653 ms | 24.31% |
| CIR-Focused-Low-CBS | 19.1 Mbps / 31.6 Kbit | 0.00% | 8.957 / 12.346 ms | 27.45% |
| Aggressive-CIR | 12.6 Mbps / 30.1 Kbit | 0.00% | 13.827 / 19.819 ms | 30.32% |
| Current-Rule | 26.4 Mbps / 131.8 Kbit | 0.00% | 55.293 / 56.841 ms | 52.61% |

### 如何解读

1. **仍然是 preliminary，不是最终规则优化结论。**
2. 小型预标定表明：调整规则参数后，Rule-Based 的 P99 和违约率可以显著改善，说明规则库并非只完成“链路打通”，后续有明确优化空间。
3. 更偏向 CIR、降低 CBS 增长、放慢回退整体上比 Current-Rule 更好，符合 Offline-Optimized 给出的启发：当前瓶颈更偏向服务速率 CIR，而不是突发容量 CBS。
4. 但预标定结果仍与 Offline-Optimized 有差距，尤其 strict profile 仍有较高违约率。因此后续需要在 OMNeT++/INET 中重新标定和验证。
5. 中期答辩中可将本轮结果作为“规则库参数预标定”材料，而不要表述为最终算法效果。

### 下一步

- [ ] 中期材料中加入“Python PoC 定位 + OMNeT++ 迁移计划”页；
- [ ] 中期材料中加入“小型规则预标定”页，说明规则库已经开始优化但未完成；
- [ ] 中期后优先调研 INET ATS/Qcr 支持情况；
- [ ] 在 OMNeT++ 中先复现静态 baseline，再迁移 Rule-Based controller。

---

## 待办（Week 2 及以后）

- [ ] M7 规则库引擎（6 规则 + 节流 + 防抖）
- [ ] 规则法 vs 静态对比图（核心图）
- [ ] M8 离线标定（替代人为试凑的参数）
- [ ] M9 基线（静态最优、固定规则）
- [ ] 参数敏感性分析
- [ ] （中期后）迁移 OMNeT++/CyclicSim 全栈仿真，对标保真度
