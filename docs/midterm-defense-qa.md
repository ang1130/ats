# 中期答辩可能问题与回答

> 用途：准备中期答辩时老师可能追问的问题。  
> 核心口径：当前阶段是 Python/SimPy preliminary PoC 收口，不是最终论文实验；规则库已完成初版和小型预标定，但后续仍需 OMNeT++/INET 高保真验证。

---

## Q1：既然后面要用 OMNeT++/INET，为什么现在还要做 Python/SimPy 仿真？

### 简短回答

当前 Python/SimPy 仿真不是为了替代 OMNeT++，而是作为快速原型平台，用来验证研究问题是否成立、规则库逻辑是否可行，以及为后续 OMNeT++ 实验提供参数范围和 baseline 参考。

### 详细回答

OMNeT++/INET 配置复杂，调试周期较长，而规则库设计需要频繁调整状态变量、阈值和 CIR/CBS 动作。如果一开始直接在 OMNeT++ 中调规则，成本会比较高。因此本阶段先用 Python/SimPy 搭建轻量级单跳 PoC，快速验证动态负载下静态参数配置是否会失效，并初步测试规则库的触发逻辑和参数调整方向。

当前 PoC 的价值主要体现在：

1. 验证动态场景下 Static-Low 确实会出现严重丢包和时延违约；
2. 验证在线调整 CIR/CBS 相比低静态配置有改善趋势；
3. 发现当前规则库与 Offline-Optimized 之间的差距；
4. 为后续 OMNeT++ 中的 baseline 和参数范围提供参考。

因此，Python/SimPy 是快速原型和预实验平台，不是最终标准仿真平台。

### 避免这样说

不要说：

> Python 仿真已经可以替代 OMNeT++。

应该说：

> Python 仿真用于前期快速验证，最终定量结论仍需 OMNeT++/INET 验证。

---

## Q2：当前 Python/SimPy PoC 与完整 IEEE 802.1Qcr ATS 有什么差距？

### 简短回答

当前 PoC 只实现了 CIR/CBS 的简化令牌桶近似，MRT 和完整 residence time / eligibility time 行为尚未完整实现，因此不能等同于完整 IEEE 802.1Qcr ATS。

### 详细回答

当前 PoC 的主要目标是验证规则库逻辑和参数调整趋势，因此采用了单跳简化模型。它与标准 ATS 的主要差距包括：

1. 只重点模拟 CIR/CBS 对关键流排队和释放的影响；
2. MRT 暂时固定，没有完整实现 maximum residence time 的标准丢弃行为；
3. 没有完整建模多跳 TSN 网络和复杂队列交互；
4. 没有与 INET/OMNeT++ 或标准实现做保真度对标；
5. 当前流量是文献参数映射和人工动态场景，不是真实工业 trace。

所以当前结果只能作为 preliminary 趋势验证。后续会迁移到 OMNeT++/INET 进行高保真验证。

---

## Q3：当前 Rule-Based 为什么不如 Offline-Optimized？这是否说明规则库没有意义？

### 简短回答

不说明规则库没有意义。当前 Rule-Based 是规则库初版，已明显优于 Static-Low，但还没有达到 Offline-Optimized 的水平。这说明在线调整方向有效，但规则参数还需要进一步标定。

### 详细回答

当前结果中，Rule-Based 相比 Static-Low 已经明显降低了丢包率和违约率。例如 relaxed profile 下：

| 方法 | 丢包率 | 违约率 |
|---|---:|---:|
| Static-Low | 39.53% | 98.78% |
| Rule-Based | 0.00% | 42.11% |

这说明在线 CIR/CBS 调整确实有改善趋势。

但 Offline-Optimized 是离线网格搜索得到的静态较优配置，它提前知道整个场景，能够选出更适合该场景的固定参数。当前 Rule-Based 是在线启发式规则库，只根据局部状态逐步调整，因此效果不如 Offline-Optimized 是合理的。

更重要的是，通过 Offline-Optimized 结果发现，当前场景更需要提高 CIR，而不是过多增加 CBS。因此后续已经做了小型规则参数预标定，说明规则库仍有优化空间。

### 避免这样说

不要说：

> Rule-Based 已经优于所有静态方法。

应该说：

> Rule-Based 相比低静态配置有明显改善，但与 Offline-Optimized 仍有差距，后续需要继续标定。

---

## Q4：当前规则库是不是只是经验启发式？创新性在哪里？

### 简短回答

当前规则库确实是轻量级启发式初版，但它的设计基于 ATS 状态变量和动态负载特征，强调可解释性和在线调整。当前创新点主要在于面向动态场景构建状态反馈规则库，并将其与 Offline-Optimized baseline 对比，为后续标准仿真和规则标定提供基础。

### 详细回答

当前规则库的设计不是单纯随意调参，而是基于以下状态变量：

```text
q, λ, d_obs, σ, token_level, drop_flag
```

对应网络中的队列积压、负载变化、时延风险、突发强度、资源水位和丢包情况。

规则库包括 R1-R6：

- R1：队列增长和到达率上升时增加 CIR；
- R2：时延接近 deadline 时提前扩容；
- R3：检测到 burst 时增加 CBS；
- R4：连续低负载时释放资源；
- R5：丢包时紧急扩容；
- R6：稳定状态下回归默认配置。

其特点是：

1. 面向 ATS 参数 CIR/CBS 的在线调整；
2. 能够解释每次调整的原因；
3. 能通过日志记录规则触发时间和动作；
4. 能与 Offline-Optimized 结果结合，反向指导规则标定。

当前还不是最终算法创新，后续创新点会进一步体现在规则标定、多场景鲁棒性和 OMNeT++ 高保真验证中。

---

## Q5：当前实验数据是怎么来的？是否可信？

### 简短回答

当前数据来自 Python/SimPy 单跳 PoC 仿真，流量参数参考文献映射，动态场景为人工设计。因此它适合作为 preliminary 趋势验证，但不能作为最终论文定量结论。

### 详细回答

实验数据主要来自：

1. `traffic_literature.yaml`：基于文献参数构造高优先级控制流、中优先级流和 BE 背景流；
2. `scenario_literature.yaml`：构造低负载—高峰—burst—回落的动态场景；
3. Python/SimPy 单跳 PoC：模拟 ATS 简化整形、出口链路和规则库调整；
4. 统计指标：丢包率、deadline violation rate、TT/ET P95/P99 delay、规则触发次数等。

当前数据的可信边界是：

- 可以说明动态负载下静态配置容易失效；
- 可以说明在线调整 CIR/CBS 有初步改善趋势；
- 可以用于中期阶段展示研究路线和问题发现；
- 不能作为最终论文定量结论；
- 后续需要 OMNeT++/INET、多 seed、多场景进一步验证。

---

## Q6：为什么要设置 relaxed 和 strict 两套 deadline profile？

### 简短回答

strict profile 用于对齐文献中的 350us/600us deadline，relaxed profile 用于在当前简化 PoC 中观察方法趋势，避免直接用严格 deadline 导致结果解释失真。

### 详细回答

文献中控制流和中优先级流的 deadline 可能是 350us 和 600us，这属于比较严格的实时要求。但当前 Python/SimPy PoC 是简化单跳模型，不是完整标准 ATS 实现，如果只使用 strict deadline，容易把模型误差和规则效果混在一起。

因此本阶段设置两套 profile：

| Profile | 用途 |
|---|---|
| relaxed | 10ms PoC deadline，用于观察规则调整趋势 |
| strict | 350us/600us 文献 deadline，用于评估与文献要求的差距 |

中期汇报时主要用 relaxed 展示方法趋势，用 strict 说明当前 PoC 与严格实时要求仍有差距。

---

## Q7：strict profile 下还有违约，是否说明方法失败？

### 简短回答

不能直接说失败。strict profile 用的是文献级严格 deadline，当前 PoC 是简化模型，因此 strict 下违约说明当前规则和模型还不足以满足严格实时要求，这正是后续 OMNeT++ 高保真验证和规则标定的重点。

### 详细回答

当前 strict profile 下，Offline-Optimized 的 violation rate 已经降到 0.04%，Rule-Based 经过小型预标定后也从 Current-Rule 的 52.61% 降到了 24.31%。这说明优化方向是有效的，但还没有完全满足严格 deadline。

原因包括：

1. 当前 PoC 不是完整 IEEE 802.1Qcr ATS；
2. 规则库参数尚未系统标定；
3. MRT 暂时固定；
4. strict deadline 本身非常严格；
5. 当前只是单场景、单 seed preliminary 验证。

所以 strict 下仍有违约并不否定研究方向，而是说明后续需要继续做标准仿真和规则优化。

---

## Q8：为什么 MRT 暂时不做？这会不会影响论文完整性？

### 简短回答

MRT 涉及 ATS 标准中的 residence time 和丢弃行为，当前单跳 Python PoC 难以严谨实现。因此中期阶段先聚焦 CIR/CBS，MRT 作为理论变量保留，并计划在 OMNeT++/INET 阶段进一步扩展。

### 详细回答

当前理论模型已经承认 ATS 的参数向量是：

```text
x = (CIR, CBS, MRT)
```

但阶段实现上采用：

```text
x_stage1 = (CIR, CBS), MRT fixed
```

这样做的原因是：

1. CIR/CBS 更容易映射到当前 PoC 的令牌桶整形逻辑；
2. MRT 涉及最大驻留时间、丢弃策略和标准 ATS 行为；
3. 如果在简化模型中强行实现 MRT，可能反而导致结论不严谨；
4. 中期阶段重点是验证动态调整方向和规则库逻辑。

后续在 OMNeT++/INET 中，如果可以使用更标准的 ATS/Qcr 模块，再逐步纳入 MRT。

---

## Q9：Offline-Optimized 是怎么得到的？是不是最终最优？

### 简短回答

Offline-Optimized 是通过 CIR/CBS 离散网格搜索得到的 preliminary 静态优化基线，不是数学意义上的全局最优，也不是文献中完整 Downhill Simplex 方法。

### 详细回答

当前搜索空间为：

```text
CIR ∈ {4, 6, 8, 10, 12, 15, 20, 30, 50 Mbps}
CBS ∈ {10, 20, 50, 100, 200 Kbit}
```

搜索目标是优先选择：

1. 无丢包；
2. deadline violation rate 不超过 epsilon；
3. 资源代价较低；
4. P99 delay 较低。

当前搜索得到的较优候选是：

```text
50 Mbps / 10 Kbit
```

但它只是当前搜索空间和当前 PoC 场景下的静态较优候选，不是最终全局最优。后续在 OMNeT++ 中还需要重新搜索或标定。

---

## Q10：为什么 Rule-Based 预标定后最终 CIR 只有 19Mbps，却比 Current-Rule 的 26.4Mbps 效果更好？

### 简短回答

这说明不只是最终 CIR 数值重要，调整时机、回退速度、CBS 增长方式和规则触发节奏也会影响排队时延。预标定结果提示当前规则需要更合理地分配 CIR/CBS 动作和回退策略。

### 详细回答

Current-Rule 最终 CIR 较高，但它在过程中可能存在：

1. 扩容时机偏晚；
2. CBS 增长过多但对持续排队帮助有限；
3. 回退策略导致高峰阶段参数不稳定；
4. 部分 backlog 已经积累，后续再提高 CIR 难以完全消除高分位时延。

预标定变体虽然最终 CIR 不是最高，但通过更快响应、减少 CBS 过度增长、放慢回退等方式，改善了动态过程中的时延表现。

这说明后续规则优化不能只看最终 CIR/CBS，而要看动态调整轨迹。

---

## Q11：当前工作的创新点可以怎么概括？

### 简短回答

当前阶段的创新点可以概括为：面向动态工业物联网场景，将 ATS 参数建模为 CIR/CBS/MRT，设计基于状态反馈的可解释规则库，并通过 preliminary PoC 与 Offline-Optimized baseline 对比，验证动态 CIR/CBS 调整的必要性和初步可行性。

### 详细回答

可以从三个层面概括：

1. **问题层面**：关注动态工业物联网中 ATS 静态参数配置难以适应负载变化的问题；
2. **方法层面**：设计基于状态变量 `q, λ, d_obs, σ, token, drop` 的 R1-R6 规则库，实现 CIR/CBS 在线调整；
3. **实验层面**：构建 Static-Low / Static-High / Offline-Optimized / Rule-Based 四组对比，并用 Offline-Optimized 反向指导规则参数预标定。

但中期阶段不应把创新点说成已经完全验证，而应强调这是阶段性方法框架和初步验证。

---

## Q12：后续 OMNeT++ 迁移具体怎么做？

### 简短回答

后续会先调研 INET 对 ATS/Qcr 的支持，然后搭建最小 TSN 拓扑，复现静态 baseline，再迁移 Rule-Based controller，最后做多场景、多 seed 和参数敏感性分析。

### 详细回答

迁移计划分为五步：

1. 调研 INET 是否支持 ATS/Qcr、eligibility time、CIR/CBS/MRT 或等价模块；
2. 搭建最小单交换机 TSN 拓扑；
3. 复现 Static-Low、Static-High、Offline-Optimized；
4. 将 R1-R6 规则库迁移为 controller 或 simple module；
5. 扩展到多 seed、多场景、多拓扑和参数敏感性分析。

当前 Python PoC 中沉淀的状态变量、baseline、规则逻辑和参数范围会作为迁移依据。

---

## Q13：如果 OMNeT++/INET 不支持完整 ATS/Qcr 怎么办？

### 简短回答

如果 INET 不支持完整 ATS/Qcr，可以采用近似模块、自定义 simple module，或者先实现 controller + 参数化 shaper 的简化版本，再逐步对齐标准行为。

### 详细回答

这是后续迁移的风险点之一。应对方案包括：

1. 调研 INET 是否已有相关 TSN queueing / shaper / eligibility time 模块；
2. 如果已有模块，则优先使用并配置 CIR/CBS/MRT；
3. 如果模块不完整，可以先用 token bucket / meter / queueing 机制近似；
4. 如果运行时无法修改参数，则考虑自定义 simple module 或 controller；
5. 在论文中明确说明仿真模型与标准 ATS 的对应关系和限制。

关键是不要把近似模型说成完整标准实现，而要说明建模边界。

---

## Q14：当前实验是否只是证明选题必要性，规则库贡献还不够？

### 简短回答

当前确实首先证明了选题必要性，但不止于此。已经实现了规则库初版、R4 修正、Offline-Optimized 对比和小型规则参数预标定。不过，规则库还不是最终成果，后续仍需系统标定和标准仿真验证。

### 详细回答

当前工作可以分成三个层次：

1. **必要性验证**：Static-Low 在动态场景下严重失效；
2. **规则库初步验证**：Rule-Based 相比 Static-Low 明显降低丢包和违约；
3. **规则库问题发现与预标定**：通过 Offline-Optimized 发现当前规则与离线较优配置存在差距，并通过小型预标定明显改善结果。

因此，当前不只是链路打通，但也还没有完成最终规则库优化。中期后重点就是继续做规则标定和 OMNeT++ 高保真验证。

---

## Q15：最终论文还需要补哪些实验？

### 简短回答

最终论文还需要 OMNeT++/INET 高保真仿真、多 seed、多场景、参数敏感性、消融实验和更正式的 baseline 对比。

### 详细回答

后续至少需要补：

1. OMNeT++/INET 静态 baseline 复现；
2. Rule-Based controller 迁移；
3. 多随机种子实验；
4. 多负载强度和多 burst 模式；
5. 不同拓扑规模；
6. 参数敏感性分析；
7. 规则消融实验；
8. 与文献方法或静态优化方法的更正式对比；
9. 如果条件允许，加入 MRT 相关实验。

---

## Q16：中期后怎么安排时间？

### 简短回答

中期后先完成 OMNeT++/INET 可行性调研和最小拓扑复现，再迁移规则库，最后进行多场景和论文级实验。

### 详细回答

计划可以分为：

| 阶段 | 工作 | 产出 |
|---|---|---|
| 阶段 1 | INET ATS/Qcr 支持调研 | 模块调研记录、可行方案 |
| 阶段 2 | 最小 TSN 拓扑搭建 | 静态 baseline 结果 |
| 阶段 3 | 动态场景复现 | 动态负载下静态配置表现 |
| 阶段 4 | Rule-Based controller 接入 | 规则库 OMNeT++ 对比结果 |
| 阶段 5 | 多场景/多 seed/参数敏感性 | 论文正式实验数据 |

---

# 答辩时总的安全表达

如果老师追问当前成果边界，可以总结为：

> 当前阶段完成的是基于文献参数的轻量级 PoC 和规则库初步验证。它证明了动态 ATS 参数优化问题具有必要性，也说明在线调整 CIR/CBS 具有初步可行性。但当前结果仍然是 preliminary，不是最终论文定量结论。中期后将迁移到 OMNeT++/INET 中进行标准化、高保真验证，并继续进行规则参数标定、多场景和多 seed 实验。

---

# 答辩时应避免的表达

不要说：

1. 当前 Python 仿真就是标准 ATS 仿真；
2. 当前 Rule-Based 已经达到最优；
3. 当前结果可以作为最终论文定量结论；
4. Offline-Optimized 是全局最优；
5. strict deadline 已经完全满足；
6. MRT 已经实现；
7. OMNeT++ 只是可选项。

建议说：

1. 当前是 preliminary PoC；
2. Rule-Based 已证明趋势，但还需标定；
3. Offline-Optimized 是当前搜索空间下的静态较优候选；
4. strict 结果用于暴露与文献要求的差距；
5. MRT 后续在标准仿真中扩展；
6. OMNeT++/INET 是中期后高保真验证重点。
