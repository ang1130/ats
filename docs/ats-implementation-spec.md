# ATS 自适应优化——实现工程规格（一个月计划详细拆解）

> 版本：v1.0｜日期：2026-07-08
> 配套：`ats-formalization.md`（理论）、`ats-rulelib-and-schedule.md`（规则库与排期）
> 本文是写代码前的工程拆解，按模块给出 输入/输出/数据结构/关键决策。

---

## 0. 总体技术决策（先定这些，后面才不返工）

| 决策项 | 选择 | 理由 |
|---|---|---|
| 仿真手段 | Python 自写离散事件仿真（不依赖 SimPy 也行，但建议用 SimPy 省事） | 单跳、轻量、可控；1 周可跑通 |
| 时间分辨率 | 微秒级（`1e-6` s） | 10ms 红线下需足够精度；令牌桶以 bits 计，时间步要细 |
| 单位 | 时间用秒（浮点），数据量用 bits，速率用 bits/s | 全程统一，避免单位错 |
| 随机性 | 固定随机种子 | 可复现对比实验 |
| 数据流 | 离散事件驱动（事件 = 包到达/令牌更新/规则评估） | 比时间步进高效且精确 |
| ATS 简化 | 实现核心令牌桶整形；ER（空闲预约）在单跳下简化处理 | 单跳无下游级联，ER 影响小；中期后全栈仿真再补完整 ER |

---

## 1. 模块清单（共 10 个模块 + 1 个报告）

```
M1 仿真内核（事件调度）
M2 链路与节点
M3 ATS 令牌桶整形器          ← 核心
M4 流量生成器（TT/ET/BE）
M5 动态事件注入
M6 状态监控器
M7 规则库引擎                ← 核心
M8 离线标定器
M9 基线实现
M10 指标采集与可视化
M11 中期报告
```

依赖关系：M1 ← M2 ← M3；M4、M5 独立；M6 依赖 M3；M7 依赖 M6、M3；M8 依赖 M3、M6；M9 依赖 M3、M8；M10 依赖所有。

---

## 2. 各模块详细规格

### M1 仿真内核（事件调度）

**职责**：维护全局时钟，按时间顺序执行事件。

**关键决策**：用 SimPy 还是自写？
- SimPy：现成的事件调度、资源占用，省 ~1 天。**推荐**。
- 自写：一个优先队列 + while 循环，~100 行，完全可控。

**接口**：
- `schedule(time, callback)`：在 time 安排一个事件
- `now`：当前仿真时间
- `run(until_time)`：运行到指定时间

**输出**：无（基础设施）

**注意**：所有随机数通过一个全局 `random.Random(seed)` 实例生成，保证可复现。

---

### M2 链路与节点

**职责**：模拟物理链路传输（带宽限制 + 传播时延）。

**数据结构**：
```
Link:
  bandwidth: bits/s      # 链路容量，如 1Gbps
  propagation_delay: s   # 传播时延，单跳很小（~几 us）
```

**行为**：包进入链路后，`传输时延 = packet.size / bandwidth`，到达对端时间为 `now + transmission_delay + propagation_delay`。

**节点**：发送端（产生包）、交换机（含 ATS）、接收端（统计时延）。

**简化**：单跳只有"发送端 → 交换机ATS → 接收端"一段，链路模型可极简。

---

### M3 ATS 令牌桶整形器（核心）

**职责**：实现 ATS 整形逻辑，参数 (r, b) 可在线修改。

**状态**：
```
ATSShaper:
  r: float          # 整形速率 bits/s（可在线改）
  b: float          # 桶容量 bits（可在线改）
  tokens: float     # 当前令牌水位 bits
  last_update: float# 上次令牌更新时间
  queue: deque      # 等待发送的包队列（FIFO）
  max_queue: int    # 队列上限（超过则丢包）
```

**核心逻辑**（每个事件触发）：
1. **令牌更新**：`tokens = min(b, tokens + r * (now - last_update))`；`last_update = now`
2. **包到达**：入队（若队列满 → 丢包，记 drop 事件）
3. **发送尝试**：队首包 size=L，若 `tokens >= L` → 消耗 L 令牌，发送；否则等待下次令牌更新事件

**关键决策——发送驱动方式**：
- 方案A：每次令牌更新后主动检查队列能否发送（推模型）
- 方案B：包到达时 + 定时器检查（拉模型）
- **推荐方案A**：令牌每更新一次（或计算下次"够发一个包"的时刻）安排一个检查事件。精确且不漏。

**在线改参接口**：
- `set_params(new_r, new_b)`：被 M7 规则库调用。改 r 影响令牌补充速率；改 b 可能立刻截断 tokens（`tokens = min(tokens, b)`）。

**ER 简化说明**：单跳下无上游级联，省略完整 ER 逻辑；记录这一简化，中期后全栈仿真补。

**输出**：每个包的整形器排队时延（用于指标 M10）。

**待标定/配置参数**：r、b 的取值范围 `[r_min, r_max]`、`[b_min, b_max]`、`max_queue`。

---

### M4 流量生成器（TT/ET/BE）

**职责**：按工业控制特征产生三类流量。

**数据结构**：
```
Packet:
  flow_id: int
  type: 'TT' | 'ET' | 'BE'
  size: bits
  gen_time: float     # 生成时间戳
  deadline: float     # TT/ET 的时延红线（D_max）
```

**三类生成器**：

| 类型 | 生成方式 | 参数（待文献定） |
|---|---|---|
| TT | 周期性：每 T_c 产生一个包 | 周期 T_c ∈ {1,2,5,10}ms；包长 L_c ∈ {512,1024}bits |
| ET | 事件驱动：由 M5 注入时产生突发 | 突发大小、包长 |
| BE | 泊松到达：按速率 λ_BE 产生 | λ_BE、包长（较大，如 8Kbits） |

**关键决策**：
- TT 流数量可变（阶跃事件改它）
- ET 不周期性产生，只在动态事件时出现
- BE 作为背景流，恒定或缓慢变化

**输出**：向 M3 的队列送包。

**参数出处要求**：T_c、L_c 等取值需在报告里注明工业文献出处（搭仿真时我帮你查）。

---

### M5 动态事件注入

**职责**：在仿真过程中制造"动态"，对应你确认的阶跃 + 突发。

**事件类型**：
```
StepEvent:
  time: float
  action: 'add_TT_flows' | 'remove_TT_flows' | 'change_BE_rate'
  params: {...}

BurstEvent:
  time: float
  intensity: int    # 突发包数
```

**示例场景脚本**（中期主实验用）：
```
t=0s:    5 条 TT 流稳定运行 + 背景 BE
t=30s:   阶跃：TT 流增至 10 条（产线换班）
t=60s:   突发：注入 ET 告警尖峰（20 个包瞬时到达）
t=90s:   阶跃：TT 流回 5 条
t=120s:  仿真结束
```

**关键决策**：场景脚本用配置文件（YAML/JSON）描述，方便跑不同场景。

**输出**：在指定时间触发 M4 改变流量模式。

---

### M6 状态监控器

**职责**：为规则库提供状态向量 s(t_k)。

**数据结构**：
```
Monitor:
  window: float              # 滑动窗口长度，如 0.5s
  history: deque             # 窗口内观测记录
  
  估计输出:
    q: float                 # 当前队列长度
    lambda: float            # 窗口内平均到达速率
    d_obs: float             # 窗口内 E2E 时延 P95
    sigma: float             # 到达速率波动度（窗口内方差）
    token_level: float       # τ/b
    drop_flag: bool          # 窗口内是否丢包
```

**采样频率**：每 `T_monitor`（如 50ms）采样一次，更新估计。

**关键决策**：
- d_obs 用 P95 而非均值（硬实时关注尾部）
- σ 用于判突发（R3 规则）

**输出**：每次采样产出 `s(t_k)`，传给 M7。

---

### M7 规则库引擎（核心）

**职责**：根据状态 s 触发规则，调整 (r, b)。

**数据结构**：
```
RuleEngine:
  rules: [Rule, ...]         # R1..R6，按优先级排序
  last_adjust_time: float
  T_cool: float              # 节流（消融实验定）
  x_current: (r, b)
  x_default: (r0, b0)        # 稳态回归目标（离线最优）
  delta_max: float           # C5 防抖单次最大调整量

Rule:
  id, priority
  condition(s) -> bool
  action(x_current) -> (Δr, Δb)
```

**执行流程**（每 T_monitor）：
```
s = monitor.sample()
if now - last_adjust_time < T_cool:
    return
for rule in rules (按优先级):
    if rule.condition(s):
        Δr, Δb = rule.action(x_current)
        # C5 防抖截断
        Δr = clip(Δr, -delta_max, delta_max)
        Δb = clip(Δb, -delta_max, delta_max)
        x_new = (r+Δr, b+Δb)
        # C3/C4 可行域截断
        x_new = clamp_to_feasible(x_new)
        shaper.set_params(x_new)
        last_adjust_time = now
        log(rule.id, s, x_new)
        break
```

**6 条规则的条件与动作**（对应规则库文档）：
- R1（队列堆积+流量上升）：`q > θ_q_hi and Δλ > θ_λ` → `r += δ_r_up`
- R2（时延逼近红线）：`d_obs > 0.8*D_max` → `r += δ_r_up, b += δ_b_up`
- R3（突发尖峰）：`σ > θ_σ and q 上升` → `b += δ_b_up`
- R4（队列空+令牌满）：`q < θ_q_lo and token_level > θ_τ_full` → `r -= δ_r_down`
- R5（丢包）：`drop_flag` → `r += δ_r_up, b += δ_b_up`
- R6（稳态回归）：`连续 W 窗无触发` → `(r,b) 向 x_default 缓慢移动`

**待标定参数**：所有 θ、δ、W、T_cool、delta_max（M8 标定）。

**输出**：参数调整日志（供 M10 可视化参数轨迹）。

---

### M8 离线标定器

**职责**：用仿真跑样本，标定 M7 的阈值参数。

**两步**：

**步骤1：采样最优参数**
- 遍历一组典型状态 s（不同 λ、不同流数）
- 对每个 s，在 (r,b) 网格上搜索，找使加权目标 f 最小的 (r*, b*)
- 产出样本集 `{(s_i, x*_i)}`

**步骤2：拟合阈值**
- 对每条规则，用样本集拟合其阈值
- 例 R1 的 θ_q_hi：取"最优 r* 显著大于默认 r0 的那些样本"的 q 分布，取某分位作为 θ_q_hi
- 可用简单统计（分位数）或轻量分类（决策树单分裂）

**搜索方法**：
- 网格搜索（简单、可并行、够用）——**推荐**
- 下坡单纯形（参照 Yoshimura，作为对照）

**关键决策**：标定结果存为配置文件，M7 加载即可用，与仿真解耦。

**输出**：标定后的参数文件 `calibrated_params.yaml`。

---

### M9 基线实现

**三个对比对象**：

| 基线 | 实现 | 说明 |
|---|---|---|
| B1 静态最优 | 离线对整个场景求最优 (r,b)，全程不变 | 参照 Yoshimura 单纯形法 |
| B2 固定规则 | 同 M7 规则，但阈值用工程经验初值，未经 M8 标定 | 验证"标定"的价值 |
| B3（可选）轻量 RL | 简单 Q-learning on 离散状态/动作 | 开销对比用，时间紧可砍 |

**关键决策**：B1、B2 必做，B3 可选。若 Week 3 落后，砍 B3 保 B1+B2。

**输出**：与主方法相同的指标（供 M10 对比）。

---

### M10 指标采集与可视化

**职责**：记录实验数据，产出对比图表。

**采集**（每包/每窗口记录）：
```
per_packet_log:
  flow_id, type, gen_time, e2e_delay, dropped

per_window_log:
  time, q, lambda, d_obs, r_current, b_current, rule_triggered
```

**聚合指标**（每个实验跑完算）：
- 平均时延 d̄、P95、P99
- 抖动 J（方差 or P99-P1）
- 吞吐 Θ
- 丢包率 P_drop
- D_max 违约率（>10ms 占比）
- 规则触发频率
- 决策时延（状态变化→参数生效）

**必出图表**（中期报告核心素材）：
1. 时延随时间曲线（规则法 vs B1 vs B2），标注阶跃/突发事件时刻
2. 时延 CDF 对比
3. 参数 (r,b) 轨迹图（展示自适应过程）
4. 节流 T_cool 消融图（5 个值的综合指标对比）
5. 柱状图：各方法在 d̄/J/Θ/P_drop/违约率 上的对比
6. 开销对比（决策时延、触发频率）—— RL 卖点图

**工具**：matplotlib，所有图脚本化（`plot_*.py`），可复跑。

---

### M11 中期报告

**结构**（按学院模板，复用开题 PPT 框架换内容）：
1. 研究背景与问题（复用开题）
2. 形式化建模（形式化文档精简版）
3. 规则库设计（规则库文档精简版）
4. 实验设置（拓扑、流量、动态场景、基线）
5. 初步结果（M10 的图 1-6）
6. 与已有工作对比（形式化文档第 11 节）
7. 下一步工作（OMNeT++ 全栈、多跳、多目标深化）
8. 答辩问题自查（见排期文档）

---

## 3. 文件结构规划（写代码时按此组织）

```
ats-sim/
├── config/
│   ├── scenario.yaml        # 动态场景脚本（M5）
│   ├── traffic.yaml         # 流量参数（M4）
│   └── calibrated_params.yaml  # 标定结果（M8 输出）
├── src/
│   ├── sim_core.py          # M1
│   ├── link.py              # M2
│   ├── ats_shaper.py        # M3  ← 核心
│   ├── traffic.py           # M4
│   ├── events.py            # M5
│   ├── monitor.py           # M6
│   ├── rule_engine.py       # M7  ← 核心
│   ├── calibration.py       # M8
│   ├── baselines.py         # M9
│   └── metrics.py           # M10
├── experiments/
│   ├── run_main.py          # 跑主实验
│   ├── run_calibration.py   # 跑标定
│   ├── run_ablation.py      # 跑消融
│   └── plots.py             # 出图
├── results/                 # 输出数据与图
└── docs/                    # 已有3份文档
```

---

## 4. 执行顺序与里程碑对应

| 周 | 完成模块 | 里程碑 |
|---|---|---|
| Week 1 | M1, M2, M3, M4（部分） | M1：静态配置出基线曲线 |
| Week 2 | M4（完）, M5, M6, M7 | M2：规则法 vs 静态对比图 |
| Week 3 | M8, M9, M10（部分） | M3：三基线对比 + 节流消融 |
| Week 4 | M10（完）, M11 | M4：报告初稿 |
| Week 5 | M11 定稿 + PPT | M5：可答辩 |

---

## 5. 待你确认/提供的最后几项

1. **Python 是否可用**：能跑 Python 即可，是否需要我连环境搭建一起做？
2. **是否用 SimPy**：推荐用（省事），需 `pip install simpy`。若不想装第三方库，我自写内核。
3. **流量参数出处**：M4 的 T_c、L_c 等取值，我搭到 M4 时去查工业文献给你出处。现在不阻塞。
4. **学院中期报告模板**：你若有模板文件，发我路径，我按模板写 M11；没有的话我用通用结构。

确认后即开始写 Week 1 代码（M1+M2+M3+M4 骨架）。
