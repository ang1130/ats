# ATS Python/SimPy Preliminary PoC

这是“动态工业物联网中异步流量整形优化研究”的单跳 Python/SimPy preliminary proof-of-concept。它用于规则逻辑、参数范围和实验协议的预筛选；**不**是完整 IEEE 802.1Qcr ATS 实现，也不产生论文最终定量结论。

详细范围、baseline 和结果边界见：

- [实验协议与结果台账](docs/preliminary-experiment-protocol.md)
- [状态与指标语义](docs/state-semantics.md)
- [OMNeT++/INET 迁移计划](../docs/omnetpp-migration-plan.md)

## 环境

建议在 Python 3.10+ 虚拟环境中运行：

```bash
cd ats-sim
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

每个新结果 JSON 会自动记录 Python、SimPy、PyYAML 版本；不要将本文件中的兼容范围误读为历史结果的精确锁定环境。

## 复跑顺序

默认 `--seed 42` 与既有主结果使用的随机种子一致。由于输出文件位于 Git 跟踪的 `results/`，建议在专用分支或 worktree 中复跑并检查 diff。

```bash
cd ats-sim

.venv/bin/python experiments/run_offline_grid_search.py --all-profiles --seed 42
.venv/bin/python experiments/run_compare_with_offline.py --all-profiles --seed 42
.venv/bin/python experiments/run_rule_calibration.py --all-profiles --seed 42
.venv/bin/python experiments/plot_preliminary_results.py --all-profiles
.venv/bin/python experiments/validate_preliminary_artifacts.py --strict-provenance
```

顺序不可交换：four-method comparison 读取同 profile、同 seed、同输入配置 fingerprint 的 Offline grid artifact；不匹配时会拒绝混用。

## 输出

| 脚本 | 输出 |
|---|---|
| `run_offline_grid_search.py` | `results/offline_grid_literature_{relaxed,strict}.json` |
| `run_compare_with_offline.py` | `results/rule_compare_with_offline_{relaxed,strict}.json` |
| `run_rule_calibration.py` | `results/rule_calibration_{relaxed,strict}.json` |
| `plot_preliminary_results.py` | 每个 profile 的四张 SVG 图 |

每个新 JSON 包含 `schema_version`、`provenance` 和确定性 `run_id`。图表 SVG 的 metadata 中记录其 comparison source run ID、profile 和 seed。

## 结果验证

对旧的已提交 artifacts 使用：

```bash
.venv/bin/python experiments/validate_preliminary_artifacts.py --legacy
```

它验证结果文件、两个 deadline profile、四种方法、grid/comparison Offline candidate 关系、图表边界注记和基本字段；旧 artifacts 缺少完整 provenance 时只会提示。

对按上述当前脚本复跑的 artifacts 使用：

```bash
.venv/bin/python experiments/validate_preliminary_artifacts.py --strict-provenance
```

该模式额外检查 grid → comparison → SVG 的 profile、seed、输入配置 fingerprint 和 run ID 链。

## Deadline profile

- `relaxed`：所有关键流使用 `traffic_literature.yaml` 中的 10 ms `D_max`，仅用于 PoC 趋势展示。
- `strict`：关键流采用文献映射的 350 µs / 600 µs deadline。

两者使用同一 2 秒动态流量轨迹。`Offline-Optimized` 是 45 点 CIR/CBS 离散搜索空间中的静态候选；strict 下的 `feasible` 指满足 PoC `epsilon=1%` 门限，不能被解释为严格 deadline 零违约。

## 重要限制

- 当前只在线调整 CIR/CBS；MRT 在配置中保留，但不会在 Python 执行路径中造成 residence-time 限制或丢弃。
- `token_level` 是虚拟 release 排程的归一化状态，可为负，并非 0–1 的物理 token fill ratio。
- `drop_rate` 以所有生成包为分母；`deadline_violation_rate` 以成功接收 TT/ET 包为分母，报告时必须同时给出。
- 此阶段不进行多 seed 聚合。`--seed` 参数和 provenance 仅为后续采用独立选择/评估协议的多 seed 验证准备。
