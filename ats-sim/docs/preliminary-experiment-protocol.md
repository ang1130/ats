# Python/SimPy Preliminary ATS PoC：实验协议与结果台账

## 1. 目的与结论边界

本协议登记当前 Python/SimPy 单跳 proof-of-concept（PoC）实验。其用途是验证以下**近似模型内的趋势**：动态工业负载下，固定 CIR/CBS 配置可能失配；基于状态反馈的 CIR/CBS 在线调整具有初步改善潜力。

> 当前结果来自指定随机 seed、单个人工构造动态场景的单跳 Python/SimPy PoC。它们不验证完整 IEEE 802.1Qcr 符合性、真实工业网络性能或论文最终量化结论。最终结论须由后续 OMNeT++/INET 的多 seed、多场景、高保真实验给出。

## 2. 当前执行模型

```text
TT/ET packet generators → ATSShaper (CIR/CBS token-bucket approximation) → EgressLink
BE packet generator ────────────────────────────────────────────────→ EgressLink
```

- 模型为单跳、单瓶颈近似；`EgressLink` 使用非抢占严格优先级出口调度。
- TT/ET 先进入 `ATSShaper`；BE 绕过 shaper、在出口处与关键流竞争。
- `ATSShaper` 使用 CIR/CBS 风格令牌桶和在线 backlog 重排，不是完整 Eligibility-Time ATS 实现。
- `MRT` 是理论模型和配置中的占位参数；当前 Python 执行路径**不会**强制 residence-time 约束、实施 MRT drop、搜索 MRT 或在线调整 MRT。

实现入口：

- `experiments/run_rule_compare.py`
- `src/ats_shaper.py`
- `src/egress.py`
- `src/monitor.py`
- `src/rule_engine.py`

状态和指标的实际代码语义见 [state-semantics.md](state-semantics.md)。

## 3. 输入、场景与随机性

| 项目 | 当前设置 |
|---|---|
| 流量配置 | `config/traffic_literature.yaml` |
| 场景配置 | `config/scenario_literature.yaml` |
| 时长 | 2.0 s |
| 负载轨迹 | 初始低负载 → 0.5 s 加入关键流 → 1.0 s 注入 ET burst → 1.5 s 移除附加流 |
| 随机性来源 | BE 到达和 ET burst offset |
| 既有主结果 seed | `42` |
| deadline profile | `relaxed` 或 `strict` |

`relaxed` 为全部关键流使用 `deadline.D_max`（当前 10 ms）的 PoC 趋势展示口径；`strict` 使用文献映射的每流 350 µs / 600 µs deadline。二者复用相同流量和动态事件，不构成两个独立流量场景。

## 4. 方法注册表

| 方法 | CIR/CBS 行为 | 当前角色 |
|---|---|---|
| Static-Low | 固定 8 Mbps / 20 Kbit | 低资源静态基线 |
| Static-High | 固定 30 Mbps / 100 Kbit | 高资源静态基线 |
| Offline-Optimized | 固定使用当前网格选出的候选 | 当前搜索空间内的静态较优候选 |
| Rule-Based | 从 Static-Low 出发，R1–R6 在线调节 CIR/CBS | 提出方法的 PoC 初版 |

Rule-Based 包含 R4 的连续低负载窗口和扩容后 hold period 迟滞。已有四个规则参数变体的比较是**小型预标定/探索性参数筛选**，不是规则优化完成或独立测试集验证。

## 5. Offline-Optimized 的定义

- 搜索脚本：`experiments/run_offline_grid_search.py`。
- 搜索空间：9 个 CIR × 5 个 CBS，共 45 个候选。
- `MRT` 不参与执行、搜索或可行性判断。
- 可行条件：`drop_rate <= 0` 且 `deadline_violation_rate <= epsilon`，其中 `epsilon = 1%`。
- 对可行候选，首先按 `cir/link_bandwidth + 0.1*(cbs/max_cbs_candidate)` 的资源评分排序，再参考 P99、drop 与 violation。

因此应称其为“**当前 CIR/CBS 离散搜索空间下的静态较优候选**”，不能称为全局最优、完整文献优化方法或最终论文最优值。strict profile 下即使候选被标为 feasible，也必须同时报告其实际非零 deadline violation rate；这只表示其满足本 PoC 的 `epsilon=1%` 门限。

## 6. 历史 artifacts 与可追溯性

已有的 `results/*.json`、`results/figures/*.svg` 是本协议建立前产生的 legacy preliminary artifacts。它们可作为中期阶段性成果，但部分旧文件不包含完整运行环境、Git revision、输入哈希、CLI 参数和结构化 provenance。

从本协议建立后，以下脚本会将 `schema_version` 和 `provenance` 写入新结果：

1. `run_offline_grid_search.py`
2. `run_compare_with_offline.py`
3. `run_rule_calibration.py`
4. `plot_preliminary_results.py`

provenance 包含 seed、profile、输入 YAML 与核心源码 SHA-256、Git revision/dirty 状态、Python/SimPy/PyYAML 版本、CLI 参数和确定性 run ID。复跑顺序及验证方式见项目 [README](../README.md)。

## 7. 中期展示的最低报告要求

展示任何数值或 SVG 时，应同时说明：

1. 这是单跳 Python/SimPy preliminary PoC；
2. 使用的 deadline profile、seed 和输入场景；
3. `drop_rate` 与 `deadline_violation_rate` 的不同分母；
4. Offline-Optimized 是离散网格得到的候选；
5. MRT 未在当前执行模型中约束或参与控制；
6. Rule-Based 相对 Static-Low 有初步改善，但当前仍需与 offline candidate、严格 profile 和后续高保真验证共同解释。
