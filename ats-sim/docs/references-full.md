# 参考文献清单

> 分三类：①开题已引用（需校园网/IEEE 下载）②开放获取（arXiv，直接下）③参数出处与经典文献。
> 标注 ★ 为必读/必复现，☆ 为参考。

---

## 一、开题已引用（需校园网 / IEEE Xplore 订阅下载）

这 4 篇是你开题报告里引用的，**必须拿到全文**，中期答辩要能讲清差异。

1. ★ **Lübeck et al. (2025)** — ATS 在非 FIFO 系统中的无界延迟问题规避（机制改进方向）
   - 关键词：ATS, non-FIFO, unbounded latency, high-reliability
   - 用途：相关工作（机制改进），与你正交
   - 检索：IEEE Xplore / Google Scholar 搜 "Lübeck asynchronous traffic shaper unbounded 2025"

2. ☆ **李琳 et al. (2025)** — HTS 混合整形，为不同流量匹配 TAS/CBS/令牌桶（混合整形方向）
   - 用途：相关工作（混合架构）
   - 检索：知网搜"李琳 混合整形 TSN 2025"或 IEEE

3. ★ **Yoshimura & Ito (2025)** — 下坡单纯形法离线计算最优 ATS 参数（参数优化方向）
   - **用途：你的直接基线 B1，必须复现**
   - 关键词：downhill simplex, Nelder-Mead, ATS parameter optimization offline
   - 检索：IEEE Xplore / Google Scholar

4. ★ **Wu et al. (2025)** — 基于队列理论动态调整令牌桶参数（自适应策略方向）
   - **用途：你方法论的启发源，需复现/适配**
   - 关键词：queue theory, token bucket, adaptive, feedback
   - 检索：IEEE Xplore / Google Scholar

> 校园网下载途径：学校图书馆 IEEE Xplore 订阅、知网（CNKI）、Google Scholar 通过学校 VPN。
> 下不到的告诉我标题，我帮找有无 arXiv 预印本或作者主页开放版。

---

## 二、开放获取（arXiv，直接下载，无需订阅）

这 3 篇是我实际查到的最新相关工作，直接可读。

5. ★ **Yu et al. (2025)** — "Efficient Adaptive Bandwidth Allocation for Deadline-Aware Online Admission Control in TSN", arXiv:2503.09093
   - 链接：https://arxiv.org/abs/2503.09093
   - **与你最接近的工作**：ATS+CBS 架构在线自适应带宽分配，网络微积分分析
   - 用途：相关工作，中期必须明确区分（他们做准入控制+带宽分配，你做整形参数自适应）
   - 关键数据：比 SOTA 多接纳 56% 流、接纳时间降 92%

6. ★ **Debnath et al. (2024)** — "CyclicSim: Comprehensive Evaluation of Cyclic Shapers in TSN", arXiv:2409.19792
   - 链接：https://arxiv.org/abs/2409.19792
   - **用途：中期后迁移 OMNeT++ 全栈仿真的框架基础**（开源 OMNeT++/INET TSN 评测）
   - 现在用：参考其流量参数设定

7. ☆ **Maile et al. (2024)** — "On the Effect of TSN Forwarding Mechanisms on Best-Effort Traffic", arXiv:2408.01330
   - 链接：https://arxiv.org/abs/2408.01330
   - 用途：ATS/CBS/ETS 对 BE 流影响的参考，设计多目标时参考

---

## 三、参数出处与经典文献

### 仿真流量参数出处

8. ★ **Craciunas et al. (2016)** — "Scheduling Real-Time Communication in IEEE 802.1Qbv Time Sensitive Networks", EMSOFT 2016
   - **用途：TT 流量参数（周期 1-10ms、帧长至 1500B）的经典出处**，你仿真参数依据
   - 检索：ACM DL / Google Scholar，EMSOFT'16
   - 注意：这是 TAS(Qbv) 调度的经典论文，但 TT 流量参数设定被广泛沿用

9. ☆ **Zhao et al.** — "Performance Comparison of IEEE 802.1 TSN Features"
   - 用途：ET 流量建模参考（泊松/突发，64-512B）
   - 检索：IEEE Xplore

### 标准与工业剖面

10. ☆ **IEC/IEEE 60802** — "TSN profile for Industrial Automation"
    - 用途：D_max=10ms 等工业时延指标的出处依据
    - 检索：IEEE Xplore / standards.ieee.org

### ATS 机制定义（必读，理解 802.1Qcr）

11. ★ **IEEE 802.1Qcr-2020** — "Local and Metropolitan Area Networks — Asynchronous Traffic Shaping"
    - 用途：ATS 标准定义，令牌桶 + ER 机制的权威出处
    - 检索：IEEE Xplore / standards.ieee.org
    - **建议优先读**，确保你的模型理解准确

### 网络微积分（C1 约束的解析工具）

12. ☆ **网络微积分教材/综述** — 用于推导 ATS 确定性时延上界 D_max^NC(r,b)
    - 推荐：Le Boudec & Thiran, "Network Calculus" (Springer, 经典教材)
    - 或 TSN 相关论文中的 NC 推导章节

---

## 补查建议（这些我没查到，建议你用校园网搜）

- **强化学习优化 ATS 的已有工作**：开题里提到"RL 方法开销大难落地"，需要找到具体的 RL-优化-TSN 整形论文作为对比（B3 基线和相关工作）
  - 检索词：reinforcement learning TSN traffic shaping / ATS deep RL scheduling
- **动态多目标优化（DMOP）方法**：你方案建模为 DMOP，需引用 DMOP 算法综述
  - 检索词：dynamic multi-objective optimization survey online
- **轻量启发式在线优化**：你强调"轻量"，需找启发式在线优化的方法学依据
  - 检索词：online heuristic optimization rule-based adaptive network

---

## 下载优先级建议

| 优先级 | 文献 | 理由 |
|---|---|---|
| P0（立刻） | 11 (802.1Qcr 标准), 8 (Craciunas), 6 (CyclicSim) | 理解 ATS 机制、定仿真参数、搭全栈基础 |
| P1（Week2前） | 3 (Yoshimura), 4 (Wu), 5 (Yu) | 基线复现 + 直接对照工作 |
| P2（中期前） | 1 (Lübeck), 2 (李琳), 7 (Maile) | 完整相关工作 |
| P3（按需） | 9, 10, 12, 补查项 | 写报告时引用支撑 |
