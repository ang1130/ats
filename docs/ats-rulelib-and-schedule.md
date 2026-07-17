# ATS 自适应规则库 v1 设计 + 一个月 Milestone 排期

> 版本：v1.1｜日期：2026-07-08  
> 配套文档：`ats-formalization.md`  
> 更新说明：根据文献阅读结果，将早期 `r/b` 表述统一修正为 `CIR/CBS/MRT`。当前阶段规则库只调整 CIR/CBS；MRT 仅保留为理论/配置占位量，Python 执行模型未实施 residence-time/MRT drop 语义。

---

# 第一部分：规则库 v1 设计草图

## 1. 设计思想

规则库 = **“监控量 → 触发条件 → 参数调整动作”** 的集合。

核心思想是将 ATS 参数配置经验转化为可执行的 if-then 规则：

> 队列堆积、到达速率上升 → 当前 CIR 不足 → 增大 CIR。  
> 时延逼近红线 → 当前服务能力或突发吸收能力不足 → 增大 CIR，必要时增大 CBS。  
> 短时突发尖峰 → 主要是突发吸收问题 → 优先增大 CBS。  
> 队列长期为空、令牌长期接近满桶 → 资源过度预留 → 降低 CIR。  

完整 ATS 参数为：

```text
x = (CIR, CBS, MRT)
```

当前阶段为降低实现复杂度，仅执行：

```text
x_stage1 = (CIR, CBS)
```

MRT 保留在理论模型和配置中，但当前 Python 执行模型不施加 residence-time/MRT drop 约束。

也就是说：

- **CIR**：当前规则库在线调整；
- **CBS**：当前规则库在线调整；
- **MRT**：理论中保留；当前 Python 执行模型未实现 residence-time 约束或 MRT 丢弃，后续在标准仿真中扩展。

---

## 2. 监控量与触发量

| 监控量 | 符号 | 用途 | 触发阈值（待标定） |
|---|---|---|---|
| ATS 队列长度 | $q$ | 识别服务能力不足 | $\theta_q^{hi}, \theta_q^{lo}$ |
| 到达速率趋势 | $\Delta\lambda$ | 识别阶跃增长 | $\theta_\lambda$ |
| 观测时延 / 红线 | $d_{obs}/D_{max}$ | 识别确定性风险 | $\theta_d^{warn}=0.8$ |
| 虚拟令牌状态 | $\tau/CBS$ | 当前 PoC 的虚拟 release 排程状态；可为负，不等同于物理满桶比例 | $\theta_\tau^{full}, \theta_\tau^{empty}$ |
| 流量波动度 | $\sigma$ | 识别突发尖峰 | $\theta_\sigma$ |
| 丢包/丢弃 | $P_{drop}$ | 紧急扩容信号 | $>0$ 即触发 |

说明：若后续引入 MRT，则还需监控 residence time，即帧在 ATS 中的驻留时间。

---

## 3. 规则库 v1（6 条）

每条规则形如：

```text
条件 Cond_i(s; θ_i) → 动作 Δx_i
```

当前阶段：

```text
Δx_i = (ΔCIR_i, ΔCBS_i, 0)
```

即 MRT 当前不参与动作或执行约束。

| # | 工况 | 触发条件 | 动作 | 直觉 |
|---|---|---|---|---|
| R1 | 队列堆积 + 流量上升 | $q>\theta_q^{hi}$ 且 $\Delta\lambda>\theta_\lambda$ | $CIR \mathrel{+}= \delta_{CIR}^{up}$ | 长期服务速率不足，需提高令牌恢复速率 |
| R2 | 时延逼近红线 | $d_{obs}>0.8D_{max}$ | $CIR \mathrel{+}= \delta_{CIR}^{up}$，必要时 $CBS \mathrel{+}=\delta_{CBS}^{up}$ | 兜底保障确定性时延 |
| R3 | 突发尖峰 | $\sigma>\theta_\sigma$ 且 $q$ 快速上升 | $CBS \mathrel{+}=\delta_{CBS}^{up}$ | 突发主要需要更大桶容量吸收 |
| R4 | 队列空 + 令牌长期满桶 | $q<\theta_q^{lo}$ 且 $\tau/CBS>\theta_\tau^{full}$ | $CIR \mathrel{-}=\delta_{CIR}^{down}$ | 服务能力过剩，降低带宽预留 |
| R5 | 丢包/丢弃 | $P_{drop}>0$ | $CIR \mathrel{+}=\delta_{CIR}^{up}$，$CBS \mathrel{+}=\delta_{CBS}^{up}$ | 紧急恢复服务能力；未来可联动 MRT |
| R6 | 稳态回归 | 连续 $W$ 个窗口无 R1–R5 触发 | $(CIR,CBS)$ 向初始 Static-Low 默认配置缓慢回归 | 避免动态事件后长期过度配置 |

### 3.1 关于 MRT

MRT 在标准 ATS 中用于限制最大驻留时间：当帧 eligibility time 超过 arrival time + MRT 时，可能被丢弃。MRT 对时延上界和丢弃率都有影响。

但当前阶段暂不在线调整 MRT，原因：

1. MRT 调整涉及丢弃策略，不只是服务速率调整；
2. MRT 过小可能增加丢弃，过大可能放宽时延约束；
3. 需要更接近标准的 ATS 实现才能严谨评估；
4. 一个月中期阶段优先验证 CIR/CBS 自适应思想。

因此，当前规则库不执行 MRT 动作或 residence-time 约束；MRT 仅作为理论/配置占位量保留。

后续扩展规则可包括：

| 未来规则 | 可能动作 |
|---|---|
| residence time 接近 MRT 且无丢包 | 适度增大 CIR/CBS |
| 丢弃主要由 MRT 过小导致 | 在约束内增大 MRT |
| MRT 过大导致尾部时延过高 | 降低 MRT 或提高 CIR |

---

## 4. 触发与节流机制

```text
每 T_monitor（如 50ms）采样一次状态 s

if 当前时间 - 上次调整时间 < T_cool:
    return  # 节流，不调整

按优先级遍历规则：R5 > R2 > R3 > R1 > R4 > R6

若某条规则满足：
    计算 ΔCIR, ΔCBS
    根据防抖约束截断单次调整幅度
    根据可行域约束裁剪 CIR/CBS
    调用 ATS.set_params(CIR, CBS)
    记录触发日志
    break
```

优先级解释：

1. **R5 丢包/丢弃**：最严重，优先处理；
2. **R2 时延逼近红线**：硬实时兜底；
3. **R3 突发尖峰**：短期吸收突发；
4. **R1 队列堆积**：常规提速；
5. **R4 资源过剩**：降速；
6. **R6 稳态回归**：最低优先级。

节流参数：

```text
T_cool ∈ {100ms, 300ms, 500ms, 1s, 2s}
```

后续通过消融实验选择。

---

## 5. 待标定参数清单

| 类别 | 参数 |
|---|---|
| 状态阈值 | $\theta_q^{hi},\theta_q^{lo},\theta_\lambda,\theta_\sigma,\theta_\tau^{full}$ |
| CIR 步长 | $\delta_{CIR}^{up},\delta_{CIR}^{down}$ |
| CBS 步长 | $\delta_{CBS}^{up},\delta_{CBS}^{down}$ |
| 节流 | $T_{cool}$ |
| 稳态窗口 | $W$ |
| 防抖 | $\Delta_{max}^{CIR},\Delta_{max}^{CBS}$ |
| 默认配置 | $(CIR_0,CBS_0,MRT_0)$ |
| 高峰配置 | $(CIR_{high},CBS_{high})$ |

这些参数不能最终靠手调，应通过离线标定确定。

---

## 6. 离线标定思路

### 6.1 标定数据来源

用文献参数构造多组场景：

- 稳态低负载；
- 阶跃高负载；
- 短时突发；
- 回落低负载；
- 不同 TT/ET/BE 混合比例。

### 6.2 标定方式

对每个场景搜索当前执行变量：

```text
CIR ∈ {若干候选速率}
CBS ∈ {若干候选桶容量}
```

MRT 不进入当前 Python PoC 的执行或搜索；待标准仿真阶段纳入。

计算每组参数下的：

- P95/P99 时延；
- Dmax 违约率；
- 丢包率；
- 平均 CIR/CBS 资源成本。

选择满足时延约束下资源成本最低的配置作为近似最优。

该过程既可作为：

1. Offline-Optimized 基线；
2. 规则阈值标定依据。

---

# 第二部分：一个月 Milestone 排期表（更新版）

> 起点：2026-07-08｜终点：约 2026-08-10  
> 原则：**先形成可解释 proof-of-concept，再补标准化仿真。**

---

> **历史排期说明：** 以下 Week 2–Week 5 清单记录 2026-07-08 的原始计划，不代表当前完成状态。当前状态见 `ats-sim/docs/preliminary-experiment-protocol.md`：R1–R6、R4 迟滞、四组比较、CIR/CBS 网格、SVG 图表与小型预标定均已完成；多 seed、多场景、MRT 执行语义和 OMNeT++/INET 验证仍属后续工作。

## Week 1：环境与最小可跑通（已完成初步版本）

- [x] 创建 `ats-sim/` 独立项目；
- [x] 搭建 Python/SimPy 仿真环境；
- [x] 实现简化 ATS 令牌桶模型；
- [x] 实现 TT/ET/BE 流量生成；
- [x] 实现动态场景初步验证；
- [x] 在 `dev-log.md` 中标注数据为 preliminary。

注意：Week 1 数据只证明仿真器可以产生“静态配置动态下失效”的现象，不作为最终实验结果。

---

## Week 2：文献参数修正 + 规则库 v1

优先级调整：在实现规则库前，先把文档和配置修正为文献一致。

- [ ] 将形式化建模统一为 CIR/CBS/MRT；
- [ ] 将规则库动作统一为 CIR/CBS；
- [ ] 新建 `traffic_literature.yaml`，参考 Yoshimura & Ito 参数；
- [ ] 实现规则库 v1（R1–R6）；
- [ ] 记录规则触发日志；
- [ ] 跑 Static-Low vs Rule-Based 第一组对比。

里程碑：

> 得到第一张“静态低配置 vs 规则自适应”的时延曲线和参数轨迹图。

---

## Week 3：基线 + 离线标定

- [ ] 实现 Static-Low；
- [ ] 实现 Static-High；
- [ ] 实现 Offline-Optimized（先用网格搜索近似 Yoshimura & Ito）；
- [ ] 实现 Fixed-Rule（未标定规则）；
- [ ] 进行初步阈值标定；
- [ ] 跑四组对比：Static-Low / Static-High / Offline-Optimized / Rule-Based。

里程碑：

> 形成可用于中期的核心实验对比表和 2–3 张图。

---

## Week 4：消融实验 + 报告材料

- [ ] 节流参数消融：100ms / 300ms / 500ms / 1s / 2s；
- [ ] 不同流量强度敏感性分析；
- [ ] 整理文献对照表；
- [ ] 整理 preliminary 实验边界声明；
- [ ] 起草中期报告实验与方法部分。

---

## Week 5：中期答辩材料

- [ ] 中期报告定稿；
- [ ] 答辩 PPT；
- [ ] 准备答辩问题：ATS 参数、MRT、离线基线、Python 仿真边界、OMNeT++ 后续计划。

---

# 第三部分：中期答辩必须能答的问题

1. **为什么从 r/b 改成 CIR/CBS/MRT？**  
   因为 ATS 文献与标准中使用 CIR/CBS/MRT 描述，r/b 是早期令牌桶简写。

2. **为什么当前只调整 CIR/CBS？**  
   MRT 涉及最大驻留时间与丢弃策略；当前 Python PoC 未执行该标准语义，避免把配置占位误作完整 ATS 机制，后续在 OMNeT++/INET 中实现和验证。

3. **和 Yoshimura & Ito 有什么区别？**  
   他们做离线静态参数优化，本研究做动态在线自适应，并可用其离线结果标定规则。

4. **和 Yu et al. 有什么区别？**  
   他们做 online admission control 和 bandwidth allocation，本研究做 ATS shaping parameters 的自适应。

5. **为什么不用 OMNeT++ 直接做？**  
   一个月内先做 proof-of-concept，降低平台风险；中期后基于 OMNeT++/INET/CyclicSim 做标准化验证。

6. **实验数据是不是最终结果？**  
   不是。Python 单跳仿真数据均标注 preliminary，仅用于验证方法可行性。

---

# 第四部分：后续代码实现注意点

1. 代码变量可保留 `r`、`b`，但文档和图表中命名为 CIR、CBS；
2. 若代码中新增 MRT，应明确其是配置占位还是已执行的 residence-time 语义；在标准仿真前不将其表述为已实现机制；
3. 所有结果图标题必须标注：`Preliminary single-hop Python simulation`；
4. 参数配置需要分两套：
   - `traffic.yaml`：当前调试配置；
   - `traffic_literature.yaml`：文献参数配置。
